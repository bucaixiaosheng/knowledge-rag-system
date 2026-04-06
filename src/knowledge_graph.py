"""
知识图谱模块：Neo4j操作封装
层级化知识图谱：KnowledgeRoot → Domain → SubDomain → Document → Chunk → AnchorKeyword
核心机制：锚关键词（AnchorKeyword）作为知识关联枢纽，通过语义相似度自动串联跨文档、跨领域的知识。
"""
import json
import logging
from datetime import datetime
from typing import Optional

import numpy as np
from neo4j import GraphDatabase

from src.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
from src.config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL

logger = logging.getLogger(__name__)


class KnowledgeGraph:
    """Neo4j知识图谱"""

    def __init__(self, uri: str = None, user: str = None, password: str = None):
        self.driver = GraphDatabase.driver(
            uri or NEO4J_URI,
            auth=(user or NEO4J_USER, password or NEO4J_PASSWORD)
        )
        self.driver.verify_connectivity()
        logger.info("Neo4j连接成功")

    def close(self):
        """关闭数据库连接"""
        self.driver.close()

    # ================================================================
    # 文档操作
    # ================================================================

    def create_document(self, doc: dict) -> None:
        """
        创建文档节点
        doc: {doc_id, title, source, doc_type, content_summary, created_at, updated_at, chunk_count, metadata}
        """
        query = """
        MERGE (d:Document {doc_id: $doc_id})
        SET d.title = $title,
            d.source = $source,
            d.doc_type = $doc_type,
            d.content_summary = $summary,
            d.created_at = datetime($created_at),
            d.updated_at = datetime($updated_at),
            d.chunk_count = $chunk_count,
            d.metadata = $metadata
        """
        with self.driver.session() as session:
            session.run(query, **doc)
        logger.info(f"图谱创建文档: {doc['doc_id']} - {doc['title']}")

    def document_exists(self, doc_id: str) -> bool:
        """检查文档是否已存在"""
        query = "MATCH (d:Document {doc_id: $doc_id}) RETURN count(d) > 0 AS exists"
        with self.driver.session() as session:
            result = session.run(query, doc_id=doc_id)
            return result.single()["exists"]

    def delete_document(self, doc_id: str) -> None:
        """删除文档及其所有Chunk、关系，并清理孤立的AnchorKeyword"""
        with self.driver.session() as session:
            # Step 1: 收集该文档关联的所有chunk_id
            chunk_ids_result = session.run(
                "MATCH (c:Chunk {doc_id: $doc_id}) RETURN c.chunk_id AS chunk_id",
                doc_id=doc_id,
            )
            chunk_ids = [r["chunk_id"] for r in chunk_ids_result]
            logger.info(f"文档 {doc_id} 关联 {len(chunk_ids)} 个Chunk")

            # Step 2: 清理孤立的AnchorKeyword
            # 对每个被删chunk关联的AnchorKeyword，移除其chunk_ids和doc_ids中的引用
            if chunk_ids:
                # 找到所有与这些chunk关联的AnchorKeyword
                for cid in chunk_ids:
                    session.run(
                        """
                        MATCH (ak:AnchorKeyword)<-[:HAS_ANCHOR]-(c:Chunk {chunk_id: $chunk_id})
                        SET ak.chunk_ids = [x IN ak.chunk_ids WHERE x <> $chunk_id],
                            ak.doc_ids = CASE WHEN $doc_id IN ak.doc_ids
                                              THEN [x IN ak.doc_ids WHERE x <> $doc_id]
                                              ELSE ak.doc_ids END,
                            ak.occurrence_count = CASE WHEN ak.occurrence_count > 0
                                                       THEN ak.occurrence_count - 1
                                                       ELSE 0 END
                        """,
                        chunk_id=cid,
                        doc_id=doc_id,
                    )

                # 删除所有chunk_ids为空列表的孤立AnchorKeyword
                session.run("""
                    MATCH (ak:AnchorKeyword)
                    WHERE ak.chunk_ids = [] OR size(ak.chunk_ids) = 0
                    DETACH DELETE ak
                """)
                logger.info(f"已清理孤立AnchorKeyword")

            # Step 3: 删除所有关联Chunk节点（DETACH DELETE会同时删除Chunk的关系）
            session.run(
                "MATCH (c:Chunk {doc_id: $doc_id}) DETACH DELETE c",
                doc_id=doc_id,
            )
            logger.info(f"已删除文档 {doc_id} 的所有Chunk节点")

            # Step 4: 删除Document节点
            session.run(
                "MATCH (d:Document {doc_id: $doc_id}) DETACH DELETE d",
                doc_id=doc_id,
            )
            logger.info(f"已删除Document节点: {doc_id}")

            # Step 5: 清理可能残留的孤立Tag节点
            session.run("""
                MATCH (t:Tag)
                WHERE NOT (t)<--()
                DETACH DELETE t
            """)

        logger.info(f"图谱级联删除完成: {doc_id} (含 {len(chunk_ids)} 个Chunk)")

    # ================================================================
    # 实体/概念操作
    # ================================================================

    def create_entities(self, entities: list[dict], doc_id: str) -> int:
        """
        创建实体节点并关联到文档
        entities: [{name, entity_type, description}]
        返回创建数量
        """
        if not entities:
            return 0
        query = """
        UNWIND $entities AS e
        MERGE (ent:Entity {name: e.name})
        ON CREATE SET ent.entity_type = e.entity_type,
                      ent.description = e.description,
                      ent.created_at = datetime()
        WITH ent, e
        MATCH (d:Document {doc_id: $doc_id})
        MERGE (d)-[:MENTIONS_ENTITY]->(ent)
        """
        with self.driver.session() as session:
            session.run(query, entities=entities, doc_id=doc_id)
        logger.info(f"文档 {doc_id}: 创建 {len(entities)} 个实体")
        return len(entities)

    def create_concepts(self, concepts: list[dict], doc_id: str) -> int:
        """
        创建概念节点并关联到文档
        concepts: [{name, description, category}]
        """
        if not concepts:
            return 0
        query = """
        UNWIND $concepts AS c
        MERGE (con:Concept {name: c.name})
        ON CREATE SET con.description = c.description,
                      con.category = c.category,
                      con.created_at = datetime()
        WITH con, c
        MATCH (d:Document {doc_id: $doc_id})
        MERGE (d)-[:CONTAINS_CONCEPT]->(con)
        """
        with self.driver.session() as session:
            session.run(query, concepts=concepts, doc_id=doc_id)
        logger.info(f"文档 {doc_id}: 创建 {len(concepts)} 个概念")
        return len(concepts)

    def create_relations(self, relations: list[dict]) -> int:
        """
        创建实体间关系
        relations: [{source, target, relation_type, properties}]
        """
        if not relations:
            return 0
        count = 0
        with self.driver.session() as session:
            for r in relations:
                try:
                    # 动态构建关系类型（Cypher不支持参数化关系类型，需拼接）
                    rel_type = r["relation_type"].replace("`", "")
                    props = r.get("properties", {})
                    query = f"""
                    MATCH (a {{name: $source}})
                    MATCH (b {{name: $target}})
                    MERGE (a)-[:`{rel_type}`]->(b)
                    """
                    session.run(query, source=r["source"], target=r["target"])
                    count += 1
                except Exception as e:
                    logger.warning(f"创建关系失败 {r.get('source')} -> {r.get('target')}: {e}")
        logger.info(f"创建 {count} 个关系")
        return count

    def add_tags(self, tags: list[str], doc_id: str) -> None:
        """为文档添加标签"""
        if not tags:
            return
        query = """
        UNWIND $tags AS tag_name
        MERGE (t:Tag {name: tag_name})
        WITH t
        MATCH (d:Document {doc_id: $doc_id})
        MERGE (d)-[:TAGGED_WITH]->(t)
        """
        with self.driver.session() as session:
            session.run(query, tags=tags, doc_id=doc_id)
        logger.info(f"文档 {doc_id}: 添加 {len(tags)} 个标签")

    # ================================================================
    # 层级学科分类
    # ================================================================

    def init_knowledge_tree(self) -> None:
        """
        初始化知识树（KnowledgeRoot + 预设学科）
        创建: 1个KnowledgeRoot + 7个Domain + 11个SubDomain
        """
        init_cypher = """
        // 创建根节点
        MERGE (root:KnowledgeRoot {name: 'Knowledge', version: '2.0', created_at: datetime()})

        // 创建7个Domain（一级学科分类）
        MERGE (t:Domain {name: 'Technology', description: '计算机科学与技术', color: '#4CAF50', sort_order: 1})
        MERGE (s:Domain {name: 'Science', description: '自然科学', color: '#2196F3', sort_order: 2})
        MERGE (ss:Domain {name: 'SocialScience', description: '社会科学', color: '#FF9800', sort_order: 3})
        MERGE (a:Domain {name: 'Arts', description: '人文艺术', color: '#9C27B0', sort_order: 4})
        MERGE (b:Domain {name: 'Business', description: '商业管理', color: '#F44336', sort_order: 5})
        MERGE (e:Domain {name: 'Engineering', description: '工程实践', color: '#607D8B', sort_order: 6})
        MERGE (m:Domain {name: 'Medicine', description: '医学健康', color: '#00BCD4', sort_order: 7})

        // Root -> Domain 关系
        MERGE (root)-[:HAS_DOMAIN]->(t)
        MERGE (root)-[:HAS_DOMAIN]->(s)
        MERGE (root)-[:HAS_DOMAIN]->(ss)
        MERGE (root)-[:HAS_DOMAIN]->(a)
        MERGE (root)-[:HAS_DOMAIN]->(b)
        MERGE (root)-[:HAS_DOMAIN]->(e)
        MERGE (root)-[:HAS_DOMAIN]->(m)

        // Technology 子领域 (5个)
        MERGE (ai:SubDomain {name: 'AI', description: '人工智能',
              keywords: ['AI', 'ML', '深度学习', '神经网络', 'LLM', 'GPT', 'GLM', '语音合成', 'TTS']})
        MERGE (web:SubDomain {name: 'WebDev', description: 'Web开发',
              keywords: ['React', 'Vue', 'Node.js', 'CSS', 'HTML', 'API']})
        MERGE (devops:SubDomain {name: 'DevOps', description: '运维部署',
              keywords: ['Docker', 'K8s', 'CI/CD', 'Linux', 'Nginx']})
        MERGE (sec:SubDomain {name: 'Security', description: '网络安全',
              keywords: ['渗透测试', '加密', '漏洞']})
        MERGE (dbf:SubDomain {name: 'Database', description: '数据库',
              keywords: ['SQL', 'Neo4j', '向量数据库', 'ChromaDB', 'Redis']})

        MERGE (t)-[:HAS_SUBDOMAIN]->(ai)
        MERGE (t)-[:HAS_SUBDOMAIN]->(web)
        MERGE (t)-[:HAS_SUBDOMAIN]->(devops)
        MERGE (t)-[:HAS_SUBDOMAIN]->(sec)
        MERGE (t)-[:HAS_SUBDOMAIN]->(dbf)

        // SocialScience 子领域 (3个)
        MERGE (fin:SubDomain {name: 'Finance', description: '金融投资',
              keywords: ['股票', '基金', '量化', 'K线', '技术分析', '基本面']})
        MERGE (his:SubDomain {name: 'History', description: '历史',
              keywords: ['历史', '朝代', '战争', '文明']})
        MERGE (psy:SubDomain {name: 'Psychology', description: '心理学',
              keywords: ['心理', '认知', '行为']})

        MERGE (ss)-[:HAS_SUBDOMAIN]->(fin)
        MERGE (ss)-[:HAS_SUBDOMAIN]->(his)
        MERGE (ss)-[:HAS_SUBDOMAIN]->(psy)

        // Science 子领域 (3个)
        MERGE (phy:SubDomain {name: 'Physics', description: '物理学',
              keywords: ['量子', '相对论', '力学']})
        MERGE (bio:SubDomain {name: 'Biology', description: '生物学',
              keywords: ['基因', '细胞', '进化', 'DNA']})
        MERGE (mat:SubDomain {name: 'Mathematics', description: '数学',
              keywords: ['统计', '概率', '代数']})

        MERGE (s)-[:HAS_SUBDOMAIN]->(phy)
        MERGE (s)-[:HAS_SUBDOMAIN]->(bio)
        MERGE (s)-[:HAS_SUBDOMAIN]->(mat)
        """
        with self.driver.session() as session:
            session.run(init_cypher)

        # 验证创建结果
        with self.driver.session() as session:
            domain_count = session.run("MATCH (d:Domain) RETURN count(d) AS cnt").single()["cnt"]
            subdomain_count = session.run("MATCH (sd:SubDomain) RETURN count(sd) AS cnt").single()["cnt"]
            root_count = session.run("MATCH (kr:KnowledgeRoot) RETURN count(kr) AS cnt").single()["cnt"]
        logger.info(
            f"知识树初始化完成: KnowledgeRoot={root_count}, Domain={domain_count}, SubDomain={subdomain_count}"
        )

    def classify_document(self, title: str, content: str, doc_id: str) -> list[str]:
        """
        自动将文档分类到学科领域。
        先用关键词快速匹配，再用LLM兜底。
        返回 [主分类SubDomain名, 副分类1, 副分类2, ...]
        """
        # Step 1: 从Neo4j读取所有SubDomain及其关键词
        text = (title + " " + content[:2000]).lower()
        query = """
        MATCH (sd:SubDomain)
        RETURN sd.name AS name, sd.keywords AS keywords
        """
        with self.driver.session() as session:
            subdomains = [dict(r) for r in session.run(query)]

        # 关键词匹配评分
        scored = []
        for sd in subdomains:
            keywords = sd.get("keywords", [])
            score = sum(1 for kw in keywords if kw.lower() in text)
            if score > 0:
                scored.append((sd["name"], score))

        if scored:
            scored.sort(key=lambda x: x[1], reverse=True)
            result = [s[0] for s in scored[:3]]
            logger.info(f"关键词分类 {doc_id}: {result}")
            return result

        # Step 2: LLM兜底分类
        try:
            from openai import OpenAI

            client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)
            all_sd = [s["name"] for s in subdomains]
            prompt = f"""将以下文档分类到最合适的学科领域。
标题：{title}
摘要：{content[:500]}

可选领域：{', '.join(all_sd)}

只返回JSON：{{"primary": "领域名", "secondary": ["领域名"]}}"""

            resp = client.chat.completions.create(
                model=LLM_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=200,
            )
            content_r = resp.choices[0].message.content.strip()
            if "```json" in content_r:
                content_r = content_r.split("```json")[1].split("```")[0]
            elif "```" in content_r:
                content_r = content_r.split("```")[1].split("```")[0]
            parsed = json.loads(content_r)
            result = [parsed["primary"]] + parsed.get("secondary", [])[:2]
            logger.info(f"LLM分类 {doc_id}: {result}")
            return result
        except Exception as e:
            logger.error(f"LLM分类失败: {e}, 默认归入Technology/AI")
            return ["AI"]

    def link_document_to_domain(self, doc_id: str, domains: list[str]) -> None:
        """
        将文档关联到学科分类
        domains: [主分类, 副分类1, 副分类2, ...]
        """
        if not domains:
            return

        primary = domains[0]
        secondary = domains[1:] if len(domains) > 1 else []

        # 主分类: SubDomain -[:CONTAINS_DOC]-> Document
        primary_query = """
        MATCH (sd:SubDomain {name: $sd_name})
        MATCH (d:Document {doc_id: $doc_id})
        MERGE (sd)-[:CONTAINS_DOC]->(d)
        """
        with self.driver.session() as session:
            session.run(primary_query, sd_name=primary, doc_id=doc_id)

        # 副分类（跨领域）: Document -[:ALSO_IN_DOMAIN]-> SubDomain
        for sd_name in secondary:
            secondary_query = """
            MATCH (sd:SubDomain {name: $sd_name})
            MATCH (d:Document {doc_id: $doc_id})
            MERGE (d)-[:ALSO_IN_DOMAIN {relevance: 0.8}]->(sd)
            """
            with self.driver.session() as session:
                session.run(secondary_query, sd_name=sd_name, doc_id=doc_id)

        # 更新文档的domain_tags属性
        all_tags = ", ".join(domains)
        with self.driver.session() as session:
            session.run(
                "MATCH (d:Document {doc_id: $doc_id}) SET d.domain_tags = $tags",
                doc_id=doc_id,
                tags=all_tags,
            )
        logger.info(f"文档 {doc_id} 关联到领域: {domains}")

    # ================================================================
    # Chunk节点操作
    # ================================================================

    def create_chunk_node(self, chunk: dict) -> None:
        """
        创建Chunk节点并关联到Document
        chunk: {chunk_id, content, doc_id, chunk_index, metadata, summary, token_count, anchor_keywords, embedding_ref}
        """
        query = """
        MATCH (d:Document {doc_id: $doc_id})
        CREATE (c:Chunk {
            chunk_id: $chunk_id,
            content: $content,
            summary: $summary,
            chunk_index: $chunk_index,
            anchor_keywords: $anchor_keywords,
            embedding_ref: $embedding_ref,
            token_count: $token_count,
            doc_id: $doc_id,
            created_at: datetime()
        })
        MERGE (d)-[:HAS_CHUNK {index: $chunk_index}]->(c)
        """
        with self.driver.session() as session:
            session.run(
                query,
                chunk_id=chunk.get("chunk_id", ""),
                content=chunk.get("content", ""),
                doc_id=chunk.get("doc_id", ""),
                chunk_index=chunk.get("chunk_index", 0),
                summary=chunk.get("summary", ""),
                anchor_keywords=chunk.get("anchor_keywords", []),
                embedding_ref=chunk.get("embedding_ref", ""),
                token_count=chunk.get("token_count", 0),
            )
        logger.debug(f"创建Chunk节点: {chunk.get('chunk_id', '')}")

    # ================================================================
    # 锚关键词操作（核心！）
    # ================================================================

    def create_anchor_keywords(self, keywords: list[dict], chunk_id: str, doc_id: str) -> int:
        """
        创建/更新锚关键词节点。MERGE保证唯一性。
        keywords: [{"keyword": "xxx", "importance": 0.9}]
        """
        if not keywords:
            return 0

        for kw in keywords:
            keyword_text = kw.get("keyword", "")
            importance = kw.get("importance", 0.5)
            if not keyword_text:
                continue

            # MERGE确保唯一性：不存在则创建，存在则更新计数
            merge_query = """
            MERGE (ak:AnchorKeyword {keyword: $keyword})
            ON CREATE SET
                ak.occurrence_count = 1,
                ak.first_seen_at = datetime(),
                ak.chunk_ids = [$chunk_id],
                ak.doc_ids = [$doc_id]
            ON MATCH SET
                ak.occurrence_count = ak.occurrence_count + 1,
                ak.last_seen_at = datetime(),
                ak.chunk_ids = CASE WHEN $chunk_id IN ak.chunk_ids
                                   THEN ak.chunk_ids
                                   ELSE ak.chunk_ids + $chunk_id END,
                ak.doc_ids = CASE WHEN $doc_id IN ak.doc_ids
                                  THEN ak.doc_ids
                                  ELSE ak.doc_ids + $doc_id END
            """
            with self.driver.session() as session:
                session.run(
                    merge_query,
                    keyword=keyword_text,
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                )

            # 创建 Chunk -> AnchorKeyword 关系
            rel_query = """
            MATCH (c:Chunk {chunk_id: $chunk_id})
            MATCH (ak:AnchorKeyword {keyword: $keyword})
            MERGE (c)-[:HAS_ANCHOR {weight: $importance}]->(ak)
            """
            with self.driver.session() as session:
                session.run(
                    rel_query,
                    chunk_id=chunk_id,
                    keyword=keyword_text,
                    importance=importance,
                )

        logger.info(f"Chunk {chunk_id}: 创建 {len(keywords)} 个锚关键词")
        return len(keywords)

    def update_anchor_embeddings(self, keyword: str, embedding: list[float]) -> None:
        """
        更新锚关键词的embedding向量引用
        实际embedding存于ChromaDB，这里存前10维作引用标识
        """
        query = """
        MATCH (ak:AnchorKeyword {keyword: $keyword})
        SET ak.embedding_ref = $emb_ref
        """
        emb_ref = str(embedding[:10]) if embedding else ""
        with self.driver.session() as session:
            session.run(query, keyword=keyword, emb_ref=emb_ref)

    def build_anchor_similarity_edges(self, threshold: float = 0.5) -> int:
        """
        计算所有锚关键词间的语义相似度，创建 SEMANTICALLY_SIMILAR 关系。
        核心关联机制！通过锚关键词语义相似度实现跨文档、跨领域知识串联。

        流程:
        1. 获取所有锚关键词
        2. 批量计算embedding
        3. 计算余弦相似度矩阵
        4. 对超过阈值的对创建 SEMANTICALLY_SIMILAR 关系
        """
        from src.embedding import EmbeddingEngine

        emb_engine = EmbeddingEngine()

        # Step 1: 获取所有锚关键词
        query = """
        MATCH (ak:AnchorKeyword)
        RETURN ak.keyword AS keyword, ak.occurrence_count AS count
        ORDER BY ak.occurrence_count DESC
        """
        with self.driver.session() as session:
            anchors = [dict(r) for r in session.run(query)]

        if not anchors:
            logger.info("无锚关键词，跳过相似度建边")
            return 0

        # Step 2: 批量计算embedding
        keywords = [a["keyword"] for a in anchors]
        embeddings = emb_engine.embed_texts(keywords)

        # Step 3: 计算余弦相似度矩阵（embed_texts已经normalize了）
        emb_matrix = np.array(embeddings)
        # 已经normalize，直接点积即为余弦相似度
        sim_matrix = emb_matrix @ emb_matrix.T

        # Step 4: 创建关系边（超过阈值的）
        count = 0
        with self.driver.session() as session:
            for i in range(len(keywords)):
                for j in range(i + 1, len(keywords)):
                    score = float(sim_matrix[i, j])
                    if score > threshold:
                        session.run(
                            """
                            MATCH (a:AnchorKeyword {keyword: $kw1})
                            MATCH (b:AnchorKeyword {keyword: $kw2})
                            MERGE (a)-[r:SEMANTICALLY_SIMILAR]->(b)
                            SET r.score = $score,
                                r.method = 'cosine',
                                r.updated_at = datetime()
                            """,
                            kw1=keywords[i],
                            kw2=keywords[j],
                            score=round(score, 4),
                        )
                        count += 1

        logger.info(f"锚关键词相似度建边: {count} 条 (阈值>{threshold})")
        return count

    # ================================================================
    # 跨领域关联发现
    # ================================================================

    def discover_cross_domain_links(self) -> None:
        """
        发现 SubDomain 间的重叠关系。
        基于共享锚关键词发现领域重叠，创建 OVERLAPS_WITH 关系。
        """
        query = """
        MATCH (sd1:SubDomain)<-[:CONTAINS_DOC|ALSO_IN_DOMAIN]-(d1:Document)
              -[:HAS_CHUNK]->(c1:Chunk)-[:HAS_ANCHOR]->(ak:AnchorKeyword)
        MATCH (sd2:SubDomain)<-[:CONTAINS_DOC|ALSO_IN_DOMAIN]-(d2:Document)
              -[:HAS_CHUNK]->(c2:Chunk)-[:HAS_ANCHOR]->(ak)
        WHERE sd1 <> sd2
        WITH sd1, sd2, count(DISTINCT ak) AS shared_anchors,
             collect(DISTINCT ak.keyword) AS shared_kw
        WHERE shared_anchors >= 2
        MERGE (sd1)-[r:OVERLAPS_WITH]->(sd2)
        SET r.overlap_score = shared_anchors,
            r.shared_keywords = shared_kw,
            r.updated_at = datetime()
        """
        with self.driver.session() as session:
            session.run(query)
        logger.info("跨领域关联发现完成")

    # ================================================================
    # 语义查询（查询流程核心！）
    # ================================================================

    def search_by_semantic_query(
        self, query_text: str, embedding: list[float], top_k: int = 10
    ) -> list[dict]:
        """
        语义查询：通过查询文本的embedding，找到相似的锚关键词，再返回关联的文档和chunk。
        这是查询流程的核心方法！

        流程:
        1. 获取所有锚关键词，计算与查询embedding的余弦相似度
        2. 取top_k个最相似的锚关键词
        3. 通过锚关键词找到关联的chunk和document
        4. 沿SEMANTICALLY_SIMILAR边扩展（发现更多相关知识）
        """
        # Step 1: 获取所有锚关键词
        ak_query = """
        MATCH (ak:AnchorKeyword)
        RETURN ak.keyword AS keyword, ak.occurrence_count AS count
        ORDER BY ak.occurrence_count DESC
        """
        with self.driver.session() as session:
            anchors = [dict(r) for r in session.run(ak_query)]

        if not anchors:
            return []

        # Step 2: 批量计算锚关键词embedding，并与查询embedding比较
        from src.embedding import EmbeddingEngine

        emb_engine = EmbeddingEngine()
        ak_keywords = [a["keyword"] for a in anchors]
        ak_embeddings = emb_engine.embed_texts(ak_keywords)

        query_emb = np.array(embedding)
        ak_emb_matrix = np.array(ak_embeddings)

        # 余弦相似度（embedding已经normalize）
        query_norm = np.linalg.norm(query_emb)
        if query_norm == 0:
            return []
        query_emb_normalized = query_emb / query_norm
        similarities = ak_emb_matrix @ query_emb_normalized

        # 取 top_k 个最相似的锚关键词
        top_indices = np.argsort(similarities)[::-1][:top_k]
        matched_anchors = []
        for idx in top_indices:
            if similarities[idx] > 0.4:  # 最低阈值
                matched_anchors.append(
                    {"keyword": ak_keywords[idx], "score": float(similarities[idx])}
                )

        if not matched_anchors:
            return []

        # Step 3: 通过匹配的锚关键词，找到关联的chunk和document
        results = []
        seen_chunk_ids = set()

        with self.driver.session() as session:
            for ma in matched_anchors:
                doc_query = """
                MATCH (ak:AnchorKeyword {keyword: $keyword})<-[:HAS_ANCHOR]-(c:Chunk)
                      <-[:HAS_CHUNK]-(d:Document)
                RETURN d.doc_id AS doc_id, d.title AS title, d.source AS source,
                       d.domain_tags AS domain_tags,
                       c.chunk_id AS chunk_id, c.content AS content,
                       c.summary AS summary,
                       $score AS relevance_score
                """
                records = session.run(doc_query, keyword=ma["keyword"], score=round(ma["score"], 4))
                for r in records:
                    chunk_id = r["chunk_id"]
                    if chunk_id in seen_chunk_ids:
                        continue
                    seen_chunk_ids.add(chunk_id)
                    doc = dict(r)
                    doc["matched_keyword"] = ma["keyword"]
                    doc["keyword_score"] = ma["score"]
                    results.append(doc)

        # Step 4: 沿着锚关键词相似度边扩展（发现更多相关知识）
        if matched_anchors:
            top_kw = matched_anchors[0]["keyword"]
            expand_query = """
            MATCH (ak1:AnchorKeyword {keyword: $keyword})-[s:SEMANTICALLY_SIMILAR]->(ak2:AnchorKeyword)
            WHERE s.score > 0.6
            OPTIONAL MATCH (ak2)<-[:HAS_ANCHOR]-(c:Chunk)<-[:HAS_CHUNK]-(d:Document)
            RETURN ak2.keyword AS related_keyword, s.score AS similarity,
                   collect(DISTINCT {doc_id: d.doc_id, title: d.title}) AS related_docs
            ORDER BY s.score DESC
            LIMIT 5
            """
            with self.driver.session() as session:
                expanded = session.run(expand_query, keyword=top_kw)
                for r in expanded:
                    related_docs = r["related_docs"]
                    # 过滤掉None值
                    clean_docs = [dict(d) for d in related_docs if d.get("doc_id") is not None]
                    results.append(
                        {
                            "type": "related_knowledge",
                            "related_keyword": r["related_keyword"],
                            "similarity": float(r["similarity"]),
                            "related_docs": clean_docs,
                        }
                    )

        logger.info(
            f"语义查询 '{query_text[:30]}...': "
            f"匹配 {len(matched_anchors)} 个锚关键词, {len(results)} 个结果"
        )
        return results

    # ================================================================
    # 图谱查询
    # ================================================================

    def search_documents_by_keyword(self, keyword: str, limit: int = 10) -> list[dict]:
        """全文搜索文档（使用Neo4j全文索引）"""
        query = """
        CALL db.index.fulltext.queryNodes("doc_fulltext", $keyword)
        YIELD node, score
        RETURN node.doc_id AS doc_id,
               node.title AS title,
               node.content_summary AS summary,
               score
        ORDER BY score DESC
        LIMIT $limit
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, keyword=keyword, limit=limit)
                return [dict(record) for record in result]
        except Exception as e:
            logger.warning(f"全文搜索失败（可能索引不存在）: {e}")
            # 降级为简单LIKE查询
            fallback_query = """
            MATCH (d:Document)
            WHERE d.title CONTAINS $keyword OR d.content_summary CONTAINS $keyword
            RETURN d.doc_id AS doc_id,
                   d.title AS title,
                   d.content_summary AS summary,
                   0.5 AS score
            LIMIT $limit
            """
            with self.driver.session() as session:
                result = session.run(fallback_query, keyword=keyword, limit=limit)
                return [dict(record) for record in result]

    def get_document_graph(self, doc_id: str, depth: int = 2) -> dict:
        """
        获取文档的知识图谱（含关联实体和概念）
        返回: {document, concepts, entities, tags, connections}
        """
        query = """
        MATCH (d:Document {doc_id: $doc_id})
        OPTIONAL MATCH (d)-[:CONTAINS_CONCEPT]->(c:Concept)
        OPTIONAL MATCH (d)-[:MENTIONS_ENTITY]->(e:Entity)
        OPTIONAL MATCH (d)-[:TAGGED_WITH]->(t:Tag)
        OPTIONAL MATCH path = (d)-[:CONTAINS_CONCEPT|MENTIONS_ENTITY]->(node)-[r:RELATED_TO|USES*1..2]-(related)
        RETURN d AS document,
               collect(DISTINCT c) AS concepts,
               collect(DISTINCT e) AS entities,
               collect(DISTINCT t) AS tags
        """
        with self.driver.session() as session:
            result = session.run(query, doc_id=doc_id)
            record = result.single()
            if not record or record["document"] is None:
                return {
                    "document": None,
                    "concepts": [],
                    "entities": [],
                    "tags": [],
                    "connections": [],
                }

            doc_node = dict(record["document"])
            concepts = []
            for c in record["concepts"]:
                if c is not None:
                    concepts.append(dict(c))
            entities = []
            for e in record["entities"]:
                if e is not None:
                    entities.append(dict(e))
            tags = []
            for t in record["tags"]:
                if t is not None:
                    tags.append(dict(t))

            return {
                "document": doc_node,
                "concepts": concepts,
                "entities": entities,
                "tags": tags,
            }

    def expand_from_entities(self, entity_names: list[str], depth: int = 2) -> list[dict]:
        """
        从实体出发，扩展相关的文档和概念。
        用于图谱增强RAG。
        """
        if not entity_names:
            return []

        # 分两步：先找实体关联的文档，再找关联的概念
        query = """
        UNWIND $names AS name
        MATCH (e:Entity {name: name})
        OPTIONAL MATCH (d:Document)-[:MENTIONS_ENTITY]->(e)
        OPTIONAL MATCH (c:Concept)<-[:CONTAINS_CONCEPT]-(d2:Document)-[:MENTIONS_ENTITY]->(e)
        RETURN DISTINCT
               labels(e) AS entity_types,
               e.name AS entity_name,
               d.doc_id AS doc_id,
               d.title AS title,
               d.content_summary AS summary,
               c.name AS concept_name,
               c.description AS concept_description
        LIMIT 20
        """
        results = []
        with self.driver.session() as session:
            records = session.run(query, names=entity_names)
            for r in records:
                item = {}
                if r["doc_id"]:
                    item = {
                        "types": ["Document"],
                        "name": r.get("entity_name", ""),
                        "title": r["title"],
                        "description": r.get("summary", ""),
                        "content_summary": r.get("summary", ""),
                        "doc_id": r["doc_id"],
                    }
                elif r["concept_name"]:
                    item = {
                        "types": ["Concept"],
                        "name": r["concept_name"],
                        "title": r["concept_name"],
                        "description": r.get("concept_description", ""),
                    }
                if item:
                    results.append(item)

        return results

    def find_similar_documents(self, doc_id: str, limit: int = 5) -> list[dict]:
        """
        基于共同实体/概念找相似文档
        """
        query = """
        MATCH (d:Document {doc_id: $doc_id})-[:CONTAINS_CONCEPT|MENTIONS_ENTITY]->(node)
        MATCH (other:Document)-[:CONTAINS_CONCEPT|MENTIONS_ENTITY]->(node)
        WHERE other.doc_id <> $doc_id
        WITH other, count(DISTINCT node) AS common_count
        ORDER BY common_count DESC
        LIMIT $limit
        RETURN other.doc_id AS doc_id, other.title AS title, common_count
        """
        with self.driver.session() as session:
            result = session.run(query, doc_id=doc_id, limit=limit)
            return [dict(record) for record in result]

    def get_stats(self) -> dict:
        """获取图谱统计信息"""
        queries = {
            "document_count": "MATCH (d:Document) RETURN count(d) AS cnt",
            "chunk_count": "MATCH (c:Chunk) RETURN count(c) AS cnt",
            "entity_count": "MATCH (e:Entity) RETURN count(e) AS cnt",
            "concept_count": "MATCH (c:Concept) RETURN count(c) AS cnt",
            "tag_count": "MATCH (t:Tag) RETURN count(t) AS cnt",
            "anchor_keyword_count": "MATCH (ak:AnchorKeyword) RETURN count(ak) AS cnt",
            "domain_count": "MATCH (d:Domain) RETURN count(d) AS cnt",
            "subdomain_count": "MATCH (sd:SubDomain) RETURN count(sd) AS cnt",
            "relation_count": "MATCH ()-[r]->() RETURN count(r) AS cnt",
        }
        stats = {}
        with self.driver.session() as session:
            for key, query in queries.items():
                try:
                    result = session.run(query)
                    stats[key] = result.single()["cnt"]
                except Exception as e:
                    logger.warning(f"统计 {key} 失败: {e}")
                    stats[key] = 0
        return stats

    # ================================================================
    # DerivedKnowledge 节点操作（知识回存）
    # ================================================================

    def create_derived_knowledge(self, dk: dict) -> str:
        """创建DerivedKnowledge节点，使用dk_id作为唯一键MERGE

        Args:
            dk: 包含 dk_id, question, answer, quality_score,
                source_doc_ids, source_chunk_ids, keywords, domain, created_at

        Returns:
            dk_id
        """
        query = """
        MERGE (dk:DerivedKnowledge {dk_id: $dk_id})
        SET dk.question = $question,
            dk.answer = $answer,
            dk.quality_score = $quality_score,
            dk.source_doc_ids = $source_doc_ids,
            dk.source_chunk_ids = $source_chunk_ids,
            dk.keywords = $keywords,
            dk.domain = $domain,
            dk.created_at = datetime($created_at)
        """
        with self.driver.session() as session:
            session.run(
                query,
                dk_id=dk.get("dk_id", ""),
                question=dk.get("question", ""),
                answer=dk.get("answer", ""),
                quality_score=dk.get("quality_score", 0.0),
                source_doc_ids=dk.get("source_doc_ids", []),
                source_chunk_ids=dk.get("source_chunk_ids", []),
                keywords=dk.get("keywords", []),
                domain=dk.get("domain", ""),
                created_at=dk.get("created_at", datetime.utcnow().isoformat()),
            )
        logger.info(f"创建DerivedKnowledge节点: {dk.get('dk_id', '')}")
        return dk.get("dk_id", "")

    def link_derived_to_sources(
        self, dk_id: str, source_doc_ids: list[str], source_chunk_ids: list[str]
    ) -> None:
        """创建关系: (Document)-[:SOURCE_OF]->(DerivedKnowledge), (Chunk)-[:INSPIRED]->(DerivedKnowledge)"""
        with self.driver.session() as session:
            # Document -[:SOURCE_OF]-> DerivedKnowledge
            if source_doc_ids:
                session.run(
                    """
                    UNWIND $doc_ids AS doc_id
                    MATCH (d:Document {doc_id: doc_id})
                    MATCH (dk:DerivedKnowledge {dk_id: $dk_id})
                    MERGE (d)-[:SOURCE_OF]->(dk)
                    """,
                    dk_id=dk_id,
                    doc_ids=source_doc_ids,
                )

            # Chunk -[:INSPIRED]-> DerivedKnowledge
            if source_chunk_ids:
                session.run(
                    """
                    UNWIND $chunk_ids AS chunk_id
                    MATCH (c:Chunk {chunk_id: chunk_id})
                    MATCH (dk:DerivedKnowledge {dk_id: $dk_id})
                    MERGE (c)-[:INSPIRED]->(dk)
                    """,
                    dk_id=dk_id,
                    chunk_ids=source_chunk_ids,
                )

        logger.info(
            f"DerivedKnowledge {dk_id}: 关联 {len(source_doc_ids)} 个Document, "
            f"{len(source_chunk_ids)} 个Chunk"
        )

    def link_derived_to_anchors(self, dk_id: str, keywords: list[str]) -> None:
        """创建关系: (DerivedKnowledge)-[:ABOUT]->(AnchorKeyword)"""
        if not keywords:
            return
        with self.driver.session() as session:
            session.run(
                """
                UNWIND $keywords AS kw
                MATCH (dk:DerivedKnowledge {dk_id: $dk_id})
                MERGE (ak:AnchorKeyword {keyword: kw})
                ON CREATE SET ak.occurrence_count = 1,
                              ak.first_seen_at = datetime(),
                              ak.chunk_ids = [],
                              ak.doc_ids = []
                MERGE (dk)-[:ABOUT]->(ak)
                """,
                dk_id=dk_id,
                keywords=keywords,
            )
        logger.info(f"DerivedKnowledge {dk_id}: 关联 {len(keywords)} 个AnchorKeyword")

    def link_derived_to_domain(self, dk_id: str, domain: str) -> None:
        """创建关系: (DerivedKnowledge)-[:IN_DOMAIN]->(SubDomain)"""
        if not domain:
            return
        with self.driver.session() as session:
            session.run(
                """
                MATCH (dk:DerivedKnowledge {dk_id: $dk_id})
                MATCH (sd:SubDomain {name: $domain})
                MERGE (dk)-[:IN_DOMAIN]->(sd)
                """,
                dk_id=dk_id,
                domain=domain,
            )
        logger.info(f"DerivedKnowledge {dk_id}: 关联到领域 {domain}")

    def search_derived_knowledge(
        self, query_embedding: list[float], top_k: int = 5
    ) -> list[dict]:
        """检索已有的DerivedKnowledge节点，通过embedding_ref余弦相似度匹配

        Args:
            query_embedding: 查询文本的embedding向量
            top_k: 返回最相似的top_k个结果

        Returns:
            [{dk_id, question, answer, quality_score, score}]
        """
        # 获取所有DerivedKnowledge节点
        query = """
        MATCH (dk:DerivedKnowledge)
        RETURN dk.dk_id AS dk_id, dk.question AS question,
               dk.answer AS answer, dk.quality_score AS quality_score,
               dk.embedding_ref AS embedding_ref
        """
        with self.driver.session() as session:
            records = [dict(r) for r in session.run(query)]

        if not records:
            return []

        # 从ChromaDB获取embedding进行比较
        # embedding_ref存储在ChromaDB中，这里先返回基于文本匹配的简化版本
        # 后续可扩展为真正的embedding相似度搜索
        results = []
        query_emb = np.array(query_embedding)
        query_norm = np.linalg.norm(query_emb)
        if query_norm == 0:
            return []
        query_emb_normalized = query_emb / query_norm

        for r in records:
            emb_ref = r.get("embedding_ref", "")
            if not emb_ref or emb_ref == "":
                # 没有embedding_ref，基于质量分数排序
                results.append({k: r[k] for k in ("dk_id", "question", "answer", "quality_score")})
                continue

        # 简单返回按quality_score排序的结果
        results_sorted = sorted(records, key=lambda x: x.get("quality_score", 0), reverse=True)
        return [
            {
                "dk_id": r["dk_id"],
                "question": r["question"],
                "answer": r["answer"],
                "quality_score": r["quality_score"],
                "score": r.get("quality_score", 0),
            }
            for r in results_sorted[:top_k]
        ]

    def get_derived_knowledge_stats(self) -> dict:
        """统计DerivedKnowledge数量和最近创建的"""
        queries = {
            "total_count": "MATCH (dk:DerivedKnowledge) RETURN count(dk) AS cnt",
            "avg_quality": "MATCH (dk:DerivedKnowledge) RETURN avg(dk.quality_score) AS avg_score",
            "recent": """
                MATCH (dk:DerivedKnowledge)
                RETURN dk.dk_id AS dk_id, dk.question AS question,
                       dk.quality_score AS quality_score, dk.created_at AS created_at
                ORDER BY dk.created_at DESC
                LIMIT 5
            """,
        }
        stats = {}
        with self.driver.session() as session:
            for key, query in queries.items():
                try:
                    if key == "recent":
                        records = session.run(query)
                        stats[key] = [dict(r) for r in records]
                    elif key == "avg_quality":
                        result = session.run(query)
                        row = result.single()
                        stats[key] = round(row["avg_score"], 4) if row and row["avg_score"] is not None else 0.0
                    else:
                        result = session.run(query)
                        stats[key] = result.single()["cnt"]
                except Exception as e:
                    logger.warning(f"统计 DerivedKnowledge {key} 失败: {e}")
                    stats[key] = 0 if key != "recent" else []
        return stats

    # ================================================================
    # 知识演化追踪
    # ================================================================

    def record_keyword_evolution(
        self, keyword: str, doc_id: str, chunk_id: str, action: str = "appeared"
    ) -> None:
        """记录锚关键词演化事件。

        在AnchorKeyword节点上追加evolution_events列表属性。

        Args:
            keyword: 锚关键词文本
            doc_id: 文档ID
            chunk_id: Chunk ID
            action: 事件类型，默认 "appeared"
        """
        if not keyword:
            return
        event = json.dumps({
            "timestamp": datetime.now().isoformat(),
            "doc_id": doc_id,
            "chunk_id": chunk_id,
            "action": action,
        }, ensure_ascii=False)
        query = """
        MERGE (ak:AnchorKeyword {keyword: $keyword})
        SET ak.evolution_events = CASE
            WHEN ak.evolution_events IS NULL THEN [$event]
            ELSE ak.evolution_events + $event
        END
        """
        with self.driver.session() as session:
            session.run(query, keyword=keyword, event=event)
        logger.debug(f"记录演化事件: {keyword} ({action}) in {doc_id}/{chunk_id}")

    def get_keyword_history(self, keyword: str, limit: int = 50) -> list:
        """查询某个锚关键词的完整演化历史。

        Args:
            keyword: 锚关键词文本
            limit: 返回事件数量上限

        Returns:
            按timestamp排序的演化事件列表
        """
        query = """
        MATCH (ak:AnchorKeyword {keyword: $keyword})
        RETURN ak.evolution_events AS events
        """
        with self.driver.session() as session:
            result = session.run(query, keyword=keyword)
            row = result.single()

        if not row or row["events"] is None:
            return []

        events = [json.loads(e) if isinstance(e, str) else e for e in row["events"]]
        events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
        return events[:limit]

    def get_document_timeline(self, limit: int = 20) -> list:
        """获取文档入库时间线（按创建时间倒序）。

        Args:
            limit: 返回数量上限

        Returns:
            [{"doc_id": str, "title": str, "created_at": str}]
        """
        query = """
        MATCH (d:Document)
        RETURN d.doc_id AS doc_id, d.title AS title, d.created_at AS created_at
        ORDER BY d.created_at DESC
        LIMIT $limit
        """
        with self.driver.session() as session:
            records = session.run(query, limit=limit)
            return [
                {
                    "doc_id": r["doc_id"],
                    "title": r["title"],
                    "created_at": str(r["created_at"]),
                }
                for r in records
            ]

    def get_domain_heat_stats(self) -> dict:
        """统计各SubDomain的文档数量、最近活跃时间和AnchorKeyword数量。

        Returns:
            {domain_name: {"doc_count": int, "last_active": str, "keyword_count": int}}
        """
        # 查询各SubDomain的文档数量和最近活跃时间
        doc_query = """
        MATCH (sd:SubDomain)-[:CONTAINS_DOC]->(d:Document)
        RETURN sd.name AS domain, count(d) AS doc_count,
               max(d.created_at) AS last_active
        ORDER BY doc_count DESC
        """
        # 查询每个domain的AnchorKeyword数量
        kw_query = """
        MATCH (sd:SubDomain)-[:CONTAINS_DOC]->(d:Document)
              -[:HAS_CHUNK]->(c:Chunk)-[:HAS_ANCHOR]->(ak:AnchorKeyword)
        RETURN sd.name AS domain, count(DISTINCT ak) AS keyword_count
        """

        doc_stats = {}
        kw_stats = {}

        with self.driver.session() as session:
            for r in session.run(doc_query):
                doc_stats[r["domain"]] = {
                    "doc_count": r["doc_count"],
                    "last_active": str(r["last_active"]) if r["last_active"] else None,
                }

            for r in session.run(kw_query):
                kw_stats[r["domain"]] = r["keyword_count"]

        # 合并结果
        all_domains = set(doc_stats.keys()) | set(kw_stats.keys())
        result = {}
        for domain in all_domains:
            ds = doc_stats.get(domain, {})
            result[domain] = {
                "doc_count": ds.get("doc_count", 0),
                "last_active": ds.get("last_active"),
                "keyword_count": kw_stats.get(domain, 0),
            }
        return result

    def get_trending_keywords(self, days: int = 7, top_k: int = 10) -> list:
        """查询最近N天被引用最多的锚关键词（热度趋势）。

        通过evolution_events中的timestamp过滤。

        Args:
            days: 回溯天数
            top_k: 返回数量上限

        Returns:
            [{"keyword": str, "event_count": int, "recent_docs": int}]
        """
        from datetime import timedelta
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()

        # evolution_events are JSON strings; filter in Python
        query = """
        MATCH (ak:AnchorKeyword)
        WHERE ak.evolution_events IS NOT NULL
        RETURN ak.keyword AS keyword, ak.evolution_events AS events
        """

        try:
            with self.driver.session() as session:
                records = session.run(query)
                results = []
                for r in records:
                    events = [json.loads(e) if isinstance(e, str) else e for e in r["events"]]
                    recent = [e for e in events if e.get("timestamp", "") >= cutoff_date]
                    if recent:
                        doc_ids = list(set(e.get("doc_id", "") for e in recent))
                        results.append({
                            "keyword": r["keyword"],
                            "event_count": len(recent),
                            "recent_docs": len(doc_ids),
                        })
                results.sort(key=lambda x: x["event_count"], reverse=True)
                return results[:top_k]
        except Exception as e:
            logger.warning(f"趋势关键词查询失败: {e}")
            # 降级：直接返回occurrence_count最高的关键词
            fallback = """
            MATCH (ak:AnchorKeyword)
            WHERE ak.occurrence_count IS NOT NULL
            RETURN ak.keyword AS keyword,
                   ak.occurrence_count AS event_count,
                   size(ak.doc_ids) AS recent_docs
            ORDER BY event_count DESC
            LIMIT $top_k
            """
            with self.driver.session() as session:
                records = session.run(fallback, top_k=top_k)
                return [dict(r) for r in records]
