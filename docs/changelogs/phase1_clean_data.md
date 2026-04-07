# Phase 1: 清理脏数据文档

## 执行时间
2026-04-07

## 操作内容
删除7篇脏数据文档（URL hash/URL片段/section header作为title的无效文档）

## 删除的文档
| # | Doc ID | 异常Title | 原因 |
|---|--------|----------|------|
| 1 | wx_7bcb1a980889 | 9R7RctHBWkhhamwwqRM80Q | URL hash作为title |
| 2 | wx_IL6Gh4KVeirtbW5XXLm65A | IL6Gh4KVeirtbW5XXLm65A | URL hash作为title |
| 3 | url_7e784a450da90938 | https://mp.weixin.qq.com/s/X | URL片段作为title |
| 4 | wx_mwFBV9K3N1eMTTzyN6IV9g | mwFBV9K3N1eMTTzyN6IV9g | URL hash作为title |
| 5 | wx_86b57b77928a | zviVbeB5miAhNiUWmHSaRQ | URL hash作为title |
| 6 | wx_MmSGgdiI5AEjOmi-cKxclA | 一、AI 视频生成模型（本地部署，告别 API） | section header作为title |
| 7 | wx_Tqfhzd7MY0kfj8BZDfOMuw | 一、前言 | section header作为title |

## 结果
- 文档数：75 → 68 ✅
- Neo4j文档数：68 ✅
- 剩余68篇title均正常 ✅

## 注意事项
- Contract中 `wx_Tqfhzd7MY0kfj8BZDfOM` 的实际doc_id为 `wx_Tqfhzd7MY0kfj8BZDfOMuw`
- ChromaDB仅4篇文档（已知不一致问题），作为独立技术债务处理
