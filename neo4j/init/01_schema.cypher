// ============================================
// 知识图谱数据模型初始化脚本 (v2.0)
// 严格按照 design document Section 5.2 + Section 6.5
// 使用 MERGE / IF NOT EXISTS 保证可重复执行
// ============================================


// ============================================
// PART 1: 约束 (Constraints) — 6个唯一性约束
// ============================================

CREATE CONSTRAINT chunk_id IF NOT EXISTS
FOR (c:Chunk) REQUIRE c.chunk_id IS UNIQUE;

CREATE CONSTRAINT doc_id IF NOT EXISTS
FOR (d:Document) REQUIRE d.doc_id IS UNIQUE;

CREATE CONSTRAINT entity_name IF NOT EXISTS
FOR (e:Entity) REQUIRE e.name IS UNIQUE;

CREATE CONSTRAINT concept_name IF NOT EXISTS
FOR (c:Concept) REQUIRE c.name IS UNIQUE;

CREATE CONSTRAINT tag_name IF NOT EXISTS
FOR (t:Tag) REQUIRE t.name IS UNIQUE;

CREATE CONSTRAINT anchor_keyword IF NOT EXISTS
FOR (ak:AnchorKeyword) REQUIRE ak.keyword IS UNIQUE;


// ============================================
// PART 2: 索引 (Indexes) — 加速查询
// ============================================

CREATE INDEX doc_source IF NOT EXISTS
FOR (d:Document) ON (d.source);

CREATE INDEX doc_type IF NOT EXISTS
FOR (d:Document) ON (d.doc_type);

CREATE INDEX doc_created IF NOT EXISTS
FOR (d:Document) ON (d.created_at);

CREATE INDEX entity_type IF NOT EXISTS
FOR (e:Entity) ON (e.entity_type);

CREATE INDEX concept_category IF NOT EXISTS
FOR (c:Concept) ON (c.category);

CREATE INDEX chunk_doc_id IF NOT EXISTS
FOR (c:Chunk) ON (c.doc_id);


// ============================================
// PART 3: 全文索引 (Fulltext Indexes)
// ============================================

CREATE FULLTEXT INDEX doc_fulltext IF NOT EXISTS
FOR (d:Document) ON EACH [d.title, d.content_summary];

CREATE FULLTEXT INDEX entity_fulltext IF NOT EXISTS
FOR (e:Entity) ON EACH [e.name, e.description];


// ============================================
// PART 4: 知识层级结构 (Section 6.5)
// KnowledgeRoot → Domain → SubDomain
// ============================================

// --- KnowledgeRoot ---
MERGE (root:KnowledgeRoot {name: 'Knowledge'})
ON CREATE SET root.version = '2.0',
              root.created_at = datetime()

// --- 7 个 Domain ---
MERGE (tech:Domain {name: 'Technology'})
  ON CREATE SET tech.description = '计算机科学与技术',
                tech.color = '#4CAF50',
                tech.sort_order = 1

MERGE (sci:Domain {name: 'Science'})
  ON CREATE SET sci.description = '自然科学',
                sci.color = '#2196F3',
                sci.sort_order = 2

MERGE (soc:Domain {name: 'SocialScience'})
  ON CREATE SET soc.description = '社会科学',
                soc.color = '#FF9800',
                soc.sort_order = 3

MERGE (art:Domain {name: 'Arts'})
  ON CREATE SET art.description = '人文艺术',
                art.color = '#9C27B0',
                art.sort_order = 4

MERGE (biz:Domain {name: 'Business'})
  ON CREATE SET biz.description = '商业管理',
                biz.color = '#F44336',
                biz.sort_order = 5

MERGE (eng:Domain {name: 'Engineering'})
  ON CREATE SET eng.description = '工程实践',
                eng.color = '#607D8B',
                eng.sort_order = 6

MERGE (med:Domain {name: 'Medicine'})
  ON CREATE SET med.description = '医学健康',
                med.color = '#00BCD4',
                med.sort_order = 7

// --- KnowledgeRoot → Domain ---
MERGE (root)-[:HAS_DOMAIN]->(tech)
MERGE (root)-[:HAS_DOMAIN]->(sci)
MERGE (root)-[:HAS_DOMAIN]->(soc)
MERGE (root)-[:HAS_DOMAIN]->(art)
MERGE (root)-[:HAS_DOMAIN]->(biz)
MERGE (root)-[:HAS_DOMAIN]->(eng)
MERGE (root)-[:HAS_DOMAIN]->(med)


// ============================================
// PART 5: 11 个 SubDomain
// ============================================

// --- Technology 子领域 (5个) ---
MERGE (ai:SubDomain {name: 'AI'})
  ON CREATE SET ai.description = '人工智能',
                ai.keywords = ['AI', 'ML', '深度学习', '神经网络', 'LLM', 'GPT', 'GLM']

MERGE (web:SubDomain {name: 'WebDev'})
  ON CREATE SET web.description = 'Web开发',
                web.keywords = ['React', 'Vue', 'Node.js', 'CSS', 'HTML', 'API']

MERGE (devops:SubDomain {name: 'DevOps'})
  ON CREATE SET devops.description = '运维部署',
                devops.keywords = ['Docker', 'K8s', 'CI/CD', 'Linux', 'Nginx']

MERGE (sec:SubDomain {name: 'Security'})
  ON CREATE SET sec.description = '网络安全',
                sec.keywords = ['渗透测试', '加密', '漏洞', '防火墙']

MERGE (db_field:SubDomain {name: 'Database'})
  ON CREATE SET db_field.description = '数据库',
                db_field.keywords = ['SQL', 'MongoDB', 'Redis', 'Neo4j', 'PostgreSQL']

// --- SocialScience 子领域 (3个) ---
MERGE (fin:SubDomain {name: 'Finance'})
  ON CREATE SET fin.description = '金融投资',
                fin.keywords = ['股票', '基金', '量化', 'K线', '技术分析', '基本面']

MERGE (his:SubDomain {name: 'History'})
  ON CREATE SET his.description = '历史',
                his.keywords = ['历史', '朝代', '战争', '文明']

MERGE (psy:SubDomain {name: 'Psychology'})
  ON CREATE SET psy.description = '心理学',
                psy.keywords = ['心理', '认知', '行为', '情感']

// --- Science 子领域 (3个) ---
MERGE (phy:SubDomain {name: 'Physics'})
  ON CREATE SET phy.description = '物理学',
                phy.keywords = ['量子', '相对论', '力学', '热力学']

MERGE (bio:SubDomain {name: 'Biology'})
  ON CREATE SET bio.description = '生物学',
                bio.keywords = ['基因', '细胞', '进化', 'DNA']

MERGE (math:SubDomain {name: 'Mathematics'})
  ON CREATE SET math.description = '数学',
                math.keywords = ['统计', '概率', '代数', '微积分']

// --- Domain → SubDomain 关系 ---
MERGE (tech)-[:HAS_SUBDOMAIN]->(ai)
MERGE (tech)-[:HAS_SUBDOMAIN]->(web)
MERGE (tech)-[:HAS_SUBDOMAIN]->(devops)
MERGE (tech)-[:HAS_SUBDOMAIN]->(sec)
MERGE (tech)-[:HAS_SUBDOMAIN]->(db_field)
MERGE (soc)-[:HAS_SUBDOMAIN]->(fin)
MERGE (soc)-[:HAS_SUBDOMAIN]->(his)
MERGE (soc)-[:HAS_SUBDOMAIN]->(psy)
MERGE (sci)-[:HAS_SUBDOMAIN]->(phy)
MERGE (sci)-[:HAS_SUBDOMAIN]->(bio)
MERGE (sci)-[:HAS_SUBDOMAIN]->(math)


// ============================================
// PART 6: 跨领域关联 (SubDomain OVERLAPS_WITH)
// AI 和 Finance 有重叠（量化交易）
// ============================================

MERGE (ai)-[:OVERLAPS_WITH {overlap_score: 5, shared_keywords: ['量化', '预测模型', '深度学习'], updated_at: datetime()}]->(fin)


// ============================================
// PART 7: 示例 Document 节点 (跨 SubDomain)
// ============================================

// --- 文档1：GLM-5 配置指南（Technology/AI）---
MERGE (doc1:Document {doc_id: 'doc_glm5_guide'})
  ON CREATE SET doc1.title = 'GLM-5 配置指南',
                doc1.source = 'MEMORY.md',
                doc1.doc_type = 'memory',
                doc1.domain_tags = ['AI', 'DevOps'],
                doc1.created_at = datetime(),
                doc1.updated_at = datetime(),
                doc1.version = 3,
                doc1.checksum = 'abc123'

// --- 文档2：股票分析完整指南（SocialScience/Finance）---
MERGE (doc2:Document {doc_id: 'doc_stock_guide'})
  ON CREATE SET doc2.title = '股票分析完整指南',
                doc2.source = 'shared-projects',
                doc2.doc_type = 'guide',
                doc2.domain_tags = ['Finance'],
                doc2.created_at = datetime(),
                doc2.updated_at = datetime(),
                doc2.version = 1,
                doc2.checksum = 'def456'

// --- 文档3：知识管理系统方案（跨领域：Technology/Database + Technology/AI）---
MERGE (doc3:Document {doc_id: 'doc_knowledge_rag'})
  ON CREATE SET doc3.title = '本地RAG + Neo4j 知识管理系统建设方案',
                doc3.source = 'workspace',
                doc3.doc_type = 'plan',
                doc3.domain_tags = ['Database', 'AI', 'DevOps'],
                doc3.created_at = datetime(),
                doc3.updated_at = datetime(),
                doc3.version = 2,
                doc3.checksum = 'ghi789'

// --- 文档4：金融AI综述（跨领域：Finance + AI）---
MERGE (doc4:Document {doc_id: 'doc_fin_ai_review'})
  ON CREATE SET doc4.title = '金融AI综述：深度学习在量化交易中的应用',
                doc4.source = 'personal',
                doc4.doc_type = 'research',
                doc4.domain_tags = ['Finance', 'AI', 'Mathematics'],
                doc4.created_at = datetime(),
                doc4.updated_at = datetime(),
                doc4.version = 1,
                doc4.checksum = 'jkl012'


// ============================================
// PART 8: CONTAINS_DOC + ALSO_IN_DOMAIN 关系
// ============================================

// SubDomain → Document (主分类)
MERGE (ai)-[:CONTAINS_DOC]->(doc1)
MERGE (fin)-[:CONTAINS_DOC]->(doc2)
MERGE (db_field)-[:CONTAINS_DOC]->(doc3)
MERGE (fin)-[:CONTAINS_DOC]->(doc4)

// Document → SubDomain (跨领域关联)
MERGE (doc3)-[:ALSO_IN_DOMAIN {relevance: 0.8}]->(ai)
MERGE (doc4)-[:ALSO_IN_DOMAIN {relevance: 0.95}]->(ai)


// ============================================
// PART 9: 示例 Chunk 节点 + HAS_CHUNK 关系
// ============================================

MERGE (chunk1:Chunk {chunk_id: 'doc_glm5_guide_001'})
  ON CREATE SET chunk1.content = 'GLM-5 API配置baseUrl为 https://open.bigmodel.cn/api/anthropic，使用anthropic-messages接口',
                chunk1.summary = 'GLM-5 API baseUrl 和接口类型配置',
                chunk1.chunk_index = 0,
                chunk1.anchor_keywords = ['GLM-5配置', 'API接口', 'baseUrl', 'anthropic-messages'],
                chunk1.embedding_ref = 'emb_glm5_001',
                chunk1.token_count = 128,
                chunk1.created_at = datetime()

MERGE (chunk2:Chunk {chunk_id: 'doc_stock_guide_003'})
  ON CREATE SET chunk2.content = '技术分析使用MACD、KDJ、RSI等指标判断买卖时机，结合成交量验证趋势',
                chunk2.summary = '股票技术分析指标使用方法',
                chunk2.chunk_index = 2,
                chunk2.anchor_keywords = ['技术分析', 'MACD', 'KDJ', 'RSI', '买卖时机'],
                chunk2.embedding_ref = 'emb_stock_003',
                chunk2.token_count = 156,
                chunk2.created_at = datetime()

MERGE (chunk3:Chunk {chunk_id: 'doc_knowledge_rag_001'})
  ON CREATE SET chunk3.content = '使用Neo4j图数据库存储知识图谱，通过锚关键词的语义相似度实现跨文档知识关联',
                chunk3.summary = 'Neo4j知识图谱锚关键词关联机制',
                chunk3.chunk_index = 0,
                chunk3.anchor_keywords = ['Neo4j', '知识图谱', '锚关键词', '语义相似度', '跨文档关联'],
                chunk3.embedding_ref = 'emb_kg_001',
                chunk3.token_count = 189,
                chunk3.created_at = datetime()

MERGE (chunk4:Chunk {chunk_id: 'doc_fin_ai_review_001'})
  ON CREATE SET chunk4.content = '深度学习模型LSTM和Transformer在股票预测中表现优异，结合技术指标数据可实现自动化量化交易',
                chunk4.summary = '深度学习在股票预测中的应用',
                chunk4.chunk_index = 0,
                chunk4.anchor_keywords = ['深度学习', '量化交易', '股票预测', 'LSTM', 'Transformer'],
                chunk4.embedding_ref = 'emb_fai_001',
                chunk4.token_count = 210,
                chunk4.created_at = datetime()

// Document → Chunk (HAS_CHUNK)
MERGE (doc1)-[:HAS_CHUNK {index: 0}]->(chunk1)
MERGE (doc2)-[:HAS_CHUNK {index: 2}]->(chunk2)
MERGE (doc3)-[:HAS_CHUNK {index: 0}]->(chunk3)
MERGE (doc4)-[:HAS_CHUNK {index: 0}]->(chunk4)


// ============================================
// PART 10: 示例 AnchorKeyword 节点
// ============================================

MERGE (ak1:AnchorKeyword {keyword: 'GLM-5配置'})
  ON CREATE SET ak1.occurrence_count = 15,
                ak1.chunk_ids = ['doc_glm5_guide_001'],
                ak1.doc_ids = ['doc_glm5_guide'],
                ak1.embedding_ref = 'emb_ak1',
                ak1.first_seen_at = datetime(),
                ak1.last_seen_at = datetime()

MERGE (ak2:AnchorKeyword {keyword: 'API接口'})
  ON CREATE SET ak2.occurrence_count = 32,
                ak2.chunk_ids = ['doc_glm5_guide_001', 'doc_knowledge_rag_001'],
                ak2.doc_ids = ['doc_glm5_guide', 'doc_knowledge_rag'],
                ak2.embedding_ref = 'emb_ak2',
                ak2.first_seen_at = datetime(),
                ak2.last_seen_at = datetime()

MERGE (ak3:AnchorKeyword {keyword: '技术分析'})
  ON CREATE SET ak3.occurrence_count = 28,
                ak3.chunk_ids = ['doc_stock_guide_003', 'doc_fin_ai_review_001'],
                ak3.doc_ids = ['doc_stock_guide', 'doc_fin_ai_review'],
                ak3.embedding_ref = 'emb_ak3',
                ak3.first_seen_at = datetime(),
                ak3.last_seen_at = datetime()

MERGE (ak4:AnchorKeyword {keyword: '深度学习'})
  ON CREATE SET ak4.occurrence_count = 45,
                ak4.chunk_ids = ['doc_knowledge_rag_001', 'doc_fin_ai_review_001'],
                ak4.doc_ids = ['doc_knowledge_rag', 'doc_fin_ai_review'],
                ak4.embedding_ref = 'emb_ak4',
                ak4.first_seen_at = datetime(),
                ak4.last_seen_at = datetime()

MERGE (ak5:AnchorKeyword {keyword: '量化交易'})
  ON CREATE SET ak5.occurrence_count = 12,
                ak5.chunk_ids = ['doc_fin_ai_review_001'],
                ak5.doc_ids = ['doc_fin_ai_review'],
                ak5.embedding_ref = 'emb_ak5',
                ak5.first_seen_at = datetime(),
                ak5.last_seen_at = datetime()

MERGE (ak6:AnchorKeyword {keyword: '知识图谱'})
  ON CREATE SET ak6.occurrence_count = 8,
                ak6.chunk_ids = ['doc_knowledge_rag_001'],
                ak6.doc_ids = ['doc_knowledge_rag'],
                ak6.embedding_ref = 'emb_ak6',
                ak6.first_seen_at = datetime(),
                ak6.last_seen_at = datetime()

MERGE (ak7:AnchorKeyword {keyword: 'Neo4j'})
  ON CREATE SET ak7.occurrence_count = 6,
                ak7.chunk_ids = ['doc_knowledge_rag_001'],
                ak7.doc_ids = ['doc_knowledge_rag'],
                ak7.embedding_ref = 'emb_ak7',
                ak7.first_seen_at = datetime(),
                ak7.last_seen_at = datetime()


// ============================================
// PART 11: HAS_ANCHOR 关系 (Chunk → AnchorKeyword, 含 weight)
// ============================================

MERGE (chunk1)-[:HAS_ANCHOR {weight: 0.95}]->(ak1)
MERGE (chunk1)-[:HAS_ANCHOR {weight: 0.7}]->(ak2)
MERGE (chunk2)-[:HAS_ANCHOR {weight: 0.9}]->(ak3)
MERGE (chunk3)-[:HAS_ANCHOR {weight: 0.85}]->(ak4)
MERGE (chunk3)-[:HAS_ANCHOR {weight: 0.9}]->(ak6)
MERGE (chunk3)-[:HAS_ANCHOR {weight: 0.8}]->(ak7)
MERGE (chunk4)-[:HAS_ANCHOR {weight: 0.95}]->(ak5)
MERGE (chunk4)-[:HAS_ANCHOR {weight: 0.8}]->(ak4)
MERGE (chunk4)-[:HAS_ANCHOR {weight: 0.6}]->(ak3)


// ============================================
// PART 12: SEMANTICALLY_SIMILAR 关系 (AnchorKeyword ↔ AnchorKeyword)
// 核心关联机制！通过语义相似度实现跨文档、跨领域知识串联
// ============================================

// "技术分析" 和 "量化交易" 高度相关（同属金融分析领域）
MERGE (ak3)-[r_ss1:SEMANTICALLY_SIMILAR]->(ak5)
  ON CREATE SET r_ss1.score = 0.85, r_ss1.method = 'cosine', r_ss1.updated_at = datetime()
  ON MATCH SET r_ss1.updated_at = datetime()

// "深度学习" 和 "量化交易" 通过 AI 在金融中的应用相关联
MERGE (ak4)-[r_ss2:SEMANTICALLY_SIMILAR]->(ak5)
  ON CREATE SET r_ss2.score = 0.78, r_ss2.method = 'cosine', r_ss2.updated_at = datetime()
  ON MATCH SET r_ss2.updated_at = datetime()

// "知识图谱" 和 "Neo4j" 强关联
MERGE (ak6)-[r_ss3:SEMANTICALLY_SIMILAR]->(ak7)
  ON CREATE SET r_ss3.score = 0.92, r_ss3.method = 'cosine', r_ss3.updated_at = datetime()
  ON MATCH SET r_ss3.updated_at = datetime()

// "API接口" 和 "知识图谱" 中等关联（知识图谱系统也有API层）
MERGE (ak2)-[r_ss4:SEMANTICALLY_SIMILAR]->(ak6)
  ON CREATE SET r_ss4.score = 0.55, r_ss4.method = 'cosine', r_ss4.updated_at = datetime()
  ON MATCH SET r_ss4.updated_at = datetime()

// "GLM-5配置" 和 "深度学习" 弱关联（GLM是深度学习模型）
MERGE (ak1)-[r_ss5:SEMANTICALLY_SIMILAR]->(ak4)
  ON CREATE SET r_ss5.score = 0.50, r_ss5.method = 'cosine', r_ss5.updated_at = datetime()
  ON MATCH SET r_ss5.updated_at = datetime()


// ============================================
// PART 13: Entity 和 Concept 节点
// ============================================

MERGE (e1:Entity {name: '智谱AI'})
  ON CREATE SET e1.entity_type = 'company',
                e1.description = '开发GLM系列大模型的公司',
                e1.aliases = ['Zhipu AI', 'zhipu']

MERGE (e2:Entity {name: 'Neo4j'})
  ON CREATE SET e2.entity_type = 'technology',
                e2.description = '原生图数据库',
                e2.aliases = ['neo4j']

MERGE (e3:Entity {name: 'Google'})
  ON CREATE SET e3.entity_type = 'company',
                e3.description = '全球科技巨头',
                e3.aliases = ['谷歌']

MERGE (c1:Concept {name: 'REST API'})
  ON CREATE SET c1.description = 'Web服务接口标准',
                c1.category = 'architecture',
                c1.abstraction_level = 'high'

MERGE (c2:Concept {name: '量化投资'})
  ON CREATE SET c2.description = '基于数学模型的系统化投资方法',
                c2.category = 'finance',
                c2.abstraction_level = 'medium'


// ============================================
// PART 14: 多种关系类型
// ============================================

// Document → Entity
MERGE (doc1)-[:AUTHORED_BY]->(e1)

// Chunk → Entity (MENTIONS_ENTITY)
MERGE (chunk1)-[:MENTIONS_ENTITY {frequency: 3}]->(e1)
MERGE (chunk3)-[:MENTIONS_ENTITY {frequency: 5}]->(e2)

// Chunk → Concept (EXPRESSES_CONCEPT)
MERGE (chunk1)-[:EXPRESSES_CONCEPT {confidence: 0.9}]->(c1)
MERGE (chunk4)-[:EXPRESSES_CONCEPT {confidence: 0.85}]->(c2)

// Entity → Concept (INSTANCE_OF)
MERGE (e1)-[:INSTANCE_OF]->(c1)


// ============================================
// 验证查询（取消注释可在 Neo4j Browser 中运行）
// ============================================

// 查询1：验证约束和索引
// SHOW CONSTRAINTS;
// SHOW INDEXES;

// 查询2：统计节点数量
// MATCH (d:Domain) RETURN count(d) AS domain_count;
// MATCH (sd:SubDomain) RETURN count(sd) AS subdomain_count;
// MATCH (ak:AnchorKeyword) RETURN count(ak) AS anchor_count;
// MATCH (d:Document) RETURN count(d) AS doc_count;

// 查询3：从任意锚关键词出发，找到所有相关知识
// MATCH path = (ak:AnchorKeyword {keyword: '量化交易'})-[:SEMANTICALLY_SIMILAR*1..3]-(related:AnchorKeyword)
// RETURN path LIMIT 50

// 查询4：找到跨领域的知识桥
// MATCH (ak1:AnchorKeyword)<-[:HAS_ANCHOR]-(:Chunk)<-[:HAS_CHUNK]-(d1:Document)-[:CONTAINS_DOC]->(sd1:SubDomain)
// MATCH (ak2:AnchorKeyword)<-[:HAS_ANCHOR]-(:Chunk)<-[:HAS_CHUNK]-(d2:Document)-[:CONTAINS_DOC]->(sd2:SubDomain)
// WHERE (ak1)-[:SEMANTICALLY_SIMILAR]->(ak2) AND sd1 <> sd2
// RETURN sd1.name, ak1.keyword, ak2.keyword, sd2.name

// 查询5：可视化整个知识图谱
// MATCH path = (root:KnowledgeRoot)-[:HAS_DOMAIN]->(d:Domain)-[:HAS_SUBDOMAIN]->(sd:SubDomain)
// OPTIONAL MATCH (sd)-[:CONTAINS_DOC]->(doc:Document)-[:HAS_CHUNK]->(c:Chunk)-[:HAS_ANCHOR]->(ak:AnchorKeyword)
// OPTIONAL MATCH (ak)-[sim:SEMANTICALLY_SIMILAR]->(ak2:AnchorKeyword)
// RETURN path LIMIT 100
