# 三晳知识库输出说明

- 资料总数：66
- 已抽取正文：65
- 待补证资料：1
- 主要文件：
  - `corpus_manifest.json`：完整清单与元数据。
  - `summary_cards.md`：每份资料的标准摘要卡。
  - `term_index.md`：术语与出处的自动归档索引。
  - `text/`：每份资料抽取后的全文文本。
  - `glossary.md`：人工定稿的核心术语表。
  - `concept_map.md`：概念关系图与教学主线。
  - `teaching_playbook.md`：回答模板与口吻边界。
  - `demo_qa.md`：验证教学模式的示例问答。

## 使用建议

- 先看 `glossary.md` 与 `concept_map.md`，建立总体地图。
- 再看 `teaching_playbook.md`，理解后续回答的固定结构。
- 需要查出处时，用 `term_index.md` 或 `scripts/query_sanxi_corpus.py` 反查原文。

## 当前限制

- `05三晳之学.doc` 目前仅纳入清单，未完成稳定正文抽取。
- 自动摘要卡偏向“摘录式整理”，最终课堂口径仍以主干资料和人工定稿文件为准。
