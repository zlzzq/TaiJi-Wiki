from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
TOPIC_SLUG = "sanxi-nine-realms"
TOPIC_TITLE = "三晳九境"
TOPIC_DIR = ROOT / "output" / "knowledge" / "compiled" / "topics" / TOPIC_SLUG
AGENT_RUNS_DIR = TOPIC_DIR / "agent_runs"


PUBLIC_QUOTES = [
    ("《07太极思维》", "生成规律——有生、有无生、无生"),
    ("《07太极思维》", "一个晳是一个圈，两个晳也是一个圈"),
    ("《55讲义第二》", "三晳本义、三晳互义，这是三晳的灵魂"),
    ("《12前后三晳》", "概念不完全一样，但它们是一脉相承的"),
    ("《33三晳讲论》", "三晳互含，一三三一"),
    ("《36三晳讲义》", "并行同在的，并没有先后高下之别"),
]


SOURCE_LINKS = [
    ("07太极思维", "../corpus/007-07.md", "直接列出三晳九境，并说明三晳、三界都要成圈。"),
    ("55讲义第二", "../corpus/057-55.md", "把三晳本义与三晳互义并列为核心，并给出本义、互义结构。"),
    ("06三晳互义", "../corpus/006-06.md", "说明三晳互义、互包含，以及生中有对有变。"),
    ("12前后三晳", "../corpus/012-12.md", "说明不同三晳口径一脉相承，并强调三晳是一个圈。"),
    ("33三晳讲论", "../corpus/034-33.md", "提供一三三一、三晳互含、三复而九的整体支撑。"),
    ("36三晳讲义", "../corpus/037-36.md", "补充生成/化生、变化/流行、并行同在等口径辨析。"),
]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")


def normalize_confidence(value: Any) -> str:
    if isinstance(value, (int, float)):
        if value >= 0.9:
            return "high"
        if value >= 0.7:
            return "medium"
        return "low"
    if isinstance(value, str) and value in {"high", "medium", "low"}:
        return value
    return "medium"


def load_agent_evidence() -> list[dict[str, Any]]:
    path = AGENT_RUNS_DIR / "round1" / "agent-a.md"
    records: list[dict[str, Any]] = []
    if path.exists():
        for line in read_text(path).splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            record["source_file"] = Path(str(record.get("source_file", ""))).name
            record["confidence"] = normalize_confidence(record.get("confidence"))
            record["public_ok"] = bool(record.get("public_ok", False))
            record.setdefault("source_title", Path(record["source_file"]).stem)
            record.setdefault("locator", "")
            record.setdefault("quote", "")
            record.setdefault("paraphrase", "")
            record.setdefault("tags", [])
            record.setdefault("claim", "")
            records.append(record)
    if not records:
        raise SystemExit(f"Missing or empty Agent A evidence output: {path}")
    return records


def validate_evidence(records: list[dict[str, Any]]) -> None:
    required = {
        "source_file",
        "source_title",
        "locator",
        "quote",
        "paraphrase",
        "tags",
        "claim",
        "confidence",
        "public_ok",
    }
    for index, record in enumerate(records, start=1):
        missing = required - set(record)
        if missing:
            raise SystemExit(f"Evidence row {index} missing fields: {sorted(missing)}")
        if record["confidence"] not in {"high", "medium", "low"}:
            raise SystemExit(f"Evidence row {index} has invalid confidence: {record['confidence']}")
        if not isinstance(record["tags"], list):
            raise SystemExit(f"Evidence row {index} tags must be a list")


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(cell.replace("\n", "<br>") for cell in row) + " |")
    return "\n".join(lines)


def short_evidence_rows(records: list[dict[str, Any]], limit: int = 16) -> list[list[str]]:
    priority_tags = {
        "三晳九境",
        "有生",
        "有无生",
        "无生",
        "有对",
        "有无对",
        "无对",
        "有变",
        "有无变",
        "无变",
        "互义",
        "一三三一",
        "一个圈",
        "口径",
    }
    selected = []
    for record in records:
        tags = set(record.get("tags", []))
        if tags & priority_tags:
            selected.append(record)
    selected = selected[:limit]
    return [
        [
            record["source_title"],
            str(record["locator"]),
            f"`{record['confidence']}`",
            record["quote"],
            record["claim"],
        ]
        for record in selected
    ]


def build_source_map(records: list[dict[str, Any]]) -> str:
    counts = Counter(record["source_title"] for record in records)
    rows = []
    for title, link, role in SOURCE_LINKS:
        rows.append([f"[{title}]({link})", str(counts.get(title, 0)), role])
    return f"""# 三晳九境专题来源图

本页记录专题编译时采用的资料分工。证据条目来自多 agent 第一轮输出，并由主流程归并为 `evidence.jsonl`。

{md_table(["资料", "证据条数", "专题用途"], rows)}

## 证据分级

- `high`：直接支撑九境表、本义/互义、圆转或口径关系。
- `medium`：支撑解释性归纳，需要在正文中软化表达。
- `low`：只作背景，不进入公开页判断。

## 使用原则

- 私版可保留来源定位和短摘句，便于回查。
- 公版只保留少量来源锚点，不公开全文路径。
- 自动编译的白话说明不替代原文引用。
"""


def build_concept_graph() -> str:
    rows = [
        ["生成", "有生", "有无生", "无生", "从万有如何成立、成形、归返上看。"],
        ["对待", "有对", "有无对", "无对", "从关系、标准、界定、相待上看。"],
        ["变化", "有变", "有无变", "无变", "从流转、转化、常变互含上看。"],
    ]
    return f"""# 三晳九境概念结构

## 一句话总纲

三晳九境不是把世界分成九个死格子，而是用生成、对待、变化三路，把有、有无、无三界贯通成一个可参、可用、可回环的观察结构。

## 九境表

{md_table(["三晳", "有", "有无", "无", "白话抓手"], rows)}

## 三层关系

- 三晳：生成、对待、变化，是进入问题的三个入口。
- 九境：每一晳沿有、有无、无展开，形成三组三境。
- 三界五境：有、有无、无不是直线台阶，而是可以回环为 `无 → 无有 → 有 → 有无 → 无` 的圆。
- 三晳互义：生中有对有变，对中有生有变，变中有生有对。没有互义，九境就会退化成表格。

## 三路解释

### 生成

生成路问的是“何以成其为有”。入门先看可见的发生和形成，再追问条件、根源、先后与归返。无生不是取消生，而是把生推到不被表面发生限制的地方看。

### 对待

对待路问的是“何以成其分别”。有对是显出的关系和比较，有无对是既见对待又不被对待封死，无对不是没有分别，而是不把分别执成唯一实相。

### 变化

变化路问的是“何以流转不住”。有变是可见转化，有无变是变与不变、常与无常之间的互含，无变不是停滞，而是把变化推到不落固定相的根本处。

## 口径差异

- `化生 / 生成`：同一脉络下的不同表达。生成便于现代讲解，化生保留先天、无中、有无相生等深层意味。
- `流行 / 变化`：变化便于入门，流行强调如水无定形、随境流转的规律意味。
- `化生、相待、流易`、`化生规、对待观、流行律`、`生成规律、对待规律、变化规律`：属于不同语境和阶段，不宜互相否定。

## 一个晳是一个圈

一个晳不是一个点，而是沿有、有无、无回环。生成不是只有有生，对待不是只有有对，变化不是只有有变。讲到无生、无对、无变以后，还要能返照有生、有对、有变。

## 三个晳也是一个圈

生成自然牵出对待与变化；对待自然牵出生成与变化；变化自然牵出生成与对待。三晳不是先后排队，而是并行同在、互相含摄。

## Mermaid 图

```mermaid
flowchart LR
  A["三晳九境"] --> B["生成"]
  A --> C["对待"]
  A --> D["变化"]

  B --> B1["有生"]
  B --> B2["有无生"]
  B --> B3["无生"]

  C --> C1["有对"]
  C --> C2["有无对"]
  C --> C3["无对"]

  D --> D1["有变"]
  D --> D2["有无变"]
  D --> D3["无变"]

  B -. "互义：生中有对有变" .-> C
  C -. "互义：对中有生有变" .-> D
  D -. "互义：变中有生有对" .-> B

  E["无"] --> F["无有"]
  F --> G["有"]
  G --> H["有无"]
  H --> E
  E -. "三界五境成圆" .-> A
```
"""


def build_teaching_lesson() -> str:
    return """# 三晳九境自问自答带学

## 1. 一句点题

三晳九境解决的不是“背九个名词”，而是训练你看一件事时，不只看它出现，还要看它怎样相待、怎样变化，并且能从有端回环到无端。

## 2. 自问自答演示

自问：三晳九境先从哪里入？

自答：先从三晳入。生成看一件事怎样成立，对待看它怎样形成关系，变化看它怎样流转转化。

自问：九境从哪里来？

自答：每一晳再沿“有、有无、无”展开。生成有有生、有无生、无生；对待有有对、有无对、无对；变化有有变、有无变、无变。

自问：为什么不能只停在“有”？

自答：只停在有生、有对、有变，就只看见显出来的现象。三晳要继续追问：它的条件在哪里，关系怎样被安立，变化背后有什么不被表象带走。

自问：互义为什么重要？

自答：因为生成里也有对待和变化，对待里也有生成和变化，变化里也有生成和对待。互义一断，三晳就变成三个标签。

自问：最后怎么收束？

自答：把九境收成一个圈。可以顺着有、有无、无讲，但不能把它讲成单向台阶；从任何一境进去，都要能回到整体。

## 3. 结构回收

这一课你只要记住：

- 先看什么：先看三晳，也就是生成、对待、变化三条主线。
- 再分什么：再把每条主线分成有、有无、无三层，形成九境。
- 最后防什么：防止把九境讲成死分类，防止把“无”讲成否定，防止把三晳拆成互不相干的三个概念。

## 4. 老师式翻转

注意了，问题不在你会不会背“有生、有无生、无生”，问题在你讲“有生”的时候，能不能同时看见里面的对待和变化。

你先别急着把话说死。说“三晳九境是最高框架”很容易，难的是你遇到一个具体问题时，能不能用它转开自己的旧判断。

你现在拿到的，多半还是听来的，不是你自己的。真正开始变成自己的时候，你会发现：九境不是拿来压人的名词，而是拿来反问自己的路。

## 5. 重练习

题目：用“三晳九境”观察“我现在学三晳”这件事。

复述：先用一句话说出三晳九境是什么，不许超过 40 个字。

改写：把“生成、对待、变化”改成三个白话问题：它怎么成？它和什么相待？它怎么变？

反问：我现在是不是只在背概念？我有没有看到自己和老师、资料、旧理解之间的对待？我有没有看到学习过程本身正在变化？

落具体例子：写三句短句，分别对应有生、有对、有变；再各补一句，往有无或无处追一层。

## 6. 讲评与下一课衔接

你回答回来后，先不急着补新概念。先看你抓住了哪一条主线，再看你哪里把话说死，最后把一句更稳的说法补出来。

下一课只推进一小步：练“生中有对有变”。也就是说，不再泛讲三晳，而是拿一个具体例子看生成里面怎样同时含着对待和变化。
"""


def build_qa_drills() -> str:
    return """# 三晳九境练习题

## 练习 1：一句话复述

要求：不用“玄”“境界很高”这类空话，用 40 字以内说明三晳九境。

参考方向：三晳九境是用生成、对待、变化三路，贯通有、有无、无的一套圆转观察法。

## 练习 2：三问落地

选一个对象：一次学习、一个念头、一段关系、一个项目。

- 生成问：它怎样出现，靠什么条件成立？
- 对待问：它和什么相对、相依、相互界定？
- 变化问：它正在怎样转化，什么变了，什么没有被变带走？

## 练习 3：九境补位

先写三句：

- 有生：这件事显出来的发生是什么？
- 有对：这件事显出来的关系是什么？
- 有变：这件事显出来的变化是什么？

再补三句：

- 有无生：哪些条件半显半隐，正在酝酿？
- 有无对：哪些关系既像对立，又能互相成就？
- 有无变：哪些变化中带着不变的方向？

最后再补三句：

- 无生：不只看发生，还要看它未发生前的根据。
- 无对：不只看对立，还要看不被对立困住的地方。
- 无变：不只看变动，还要看变动中不随相走的地方。

## 练习 4：误区自查

写完以后检查五句：

- 我是不是把九境写成九个固定等级？
- 我是不是把“无”写成了什么都没有？
- 我是不是只贴标签，没有改变看问题的方式？
- 我是不是把一种口径说成唯一正路？
- 我是不是把有、有无、无写成单向台阶，没有回环？

## 练习 5：讲给别人听

用四段讲：

1. 点题：三晳九境解决什么问题。
2. 白话：生成、对待、变化分别问什么。
3. 体系：九境怎样从有、有无、无展开。
4. 收束：为什么它不是九个死格子，而是一个圆。
"""


def build_private_dossier(records: list[dict[str, Any]]) -> str:
    evidence_table = md_table(
        ["资料", "定位", "强度", "短摘句", "支撑判断"],
        short_evidence_rows(records),
    )
    source_rows = [[f"[{title}]({link})", role] for title, link, role in SOURCE_LINKS]
    return f"""# 三晳九境

## 一句点题

三晳九境是在训练一种圆转的看法：从生成、对待、变化三路进入，再把每一路贯通到有、有无、无，最后防止自己把任何一端执成死见。

## 来源与证据

{md_table(["资料", "专题用途"], source_rows)}

## 证据索引

{evidence_table}

## 九境总表

{md_table(["三晳", "有", "有无", "无", "说明"], [
    ["生成", "有生", "有无生", "无生", "看万有如何出现、成形、归返。"],
    ["对待", "有对", "有无对", "无对", "看关系、标准、界定如何成立，又如何被透开。"],
    ["变化", "有变", "有无变", "无变", "看流转、转化、常变互含如何发生。"],
])}

## 生成：有生、有无生、无生

生成不是只问“它发生了吗”，而是问“它凭什么发生、怎样成形、从哪里来又归向哪里”。有生是显出的发生，有无生是条件、酝酿、先后之间的过渡，无生不是没有生，而是不把生只看成表面现象。

## 对待：有对、有无对、无对

对待不是简单二元对立。有对是显出的对应和比较，有无对是既见对待又不被对待封死，无对不是取消分别，而是不把分别执为唯一真实。

## 变化：有变、有无变、无变

变化不是只看表面变动。有变是可见转化，有无变是变与不变、常与无常的互含，无变不是停滞，而是把变化推到不落固定相的根本处。

## 为什么九境不是九个死境界

九境可以先用表格入门，但不能止于表格。若把九境讲成九个固定层级，就丢掉了三晳最关键的互义。生成中有对待和变化，对待中有生成和变化，变化中有生成和对待。一个晳能牵出三个晳，三个晳又回到一体，这才是九境的活处。

## 与三界、五境、本义、互义的关系

- 三界：有、有无、无，是九境展开的纵向口径。
- 五境：`无 → 无有 → 有 → 有无 → 无`，把三界讲成回环。
- 本义：生成、对待、变化各自的基本义理。
- 互义：每一晳都含另外两晳，使三晳不散成三个概念。
- 一三三一：一中含三，三中归一，三复而九，九九归一。

## 自问自答带学

见 [三晳九境自问自答带学](sanxi-nine-realms-teaching-lesson.md)。

## 重练习

见 [三晳九境练习题](sanxi-nine-realms-qa-drills.md)。

## 回到原文

- [07太极思维](../corpus/007-07.md)
- [55讲义第二](../corpus/057-55.md)
- [06三晳互义](../corpus/006-06.md)
- [12前后三晳](../corpus/012-12.md)
- [33三晳讲论](../corpus/034-33.md)
- [36三晳讲义](../corpus/037-36.md)
"""


def build_public_page() -> str:
    quote_rows = [[source, f"“{quote}”"] for source, quote in PUBLIC_QUOTES]
    return f"""# 三晳九境

## 一句点题

三晳九境不是九个固定名词，而是一种训练看问题的方式：从生成、对待、变化三路进入，把有、有无、无看成一个能回环的整体。

## 九境总表

{md_table(["三晳", "有", "有无", "无", "白话抓手"], [
    ["生成", "有生", "有无生", "无生", "这件事怎样出现、成形，又怎样回到更深的根据。"],
    ["对待", "有对", "有无对", "无对", "关系、分别、标准怎样成立，又怎样不被对立困住。"],
    ["变化", "有变", "有无变", "无变", "流转和转化怎样发生，变中有什么不被带走。"],
])}

## 白话说明

入门时，先把三晳当成三个问题：

- 生成：这件事从哪里来，靠什么条件成立？
- 对待：它和什么相对、相依、相互界定？
- 变化：它在什么条件下转化，哪些地方变，哪些地方不变？

九境就是把这三个问题各自再推一层：不只看显出来的有，也看半显半隐的有无，还要追到不被表面现象限定的无。这里的“无”不是否定一切，而是防止自己只卡在现象上。

更关键的是互义：生成里有对待和变化，对待里有生成和变化，变化里有生成和对待。所以三晳不是三个工具的并列清单，而是一个互相牵引、互相成全的整体。

## 一张图

```mermaid
flowchart LR
  A["三晳九境"] --> B["生成"]
  A --> C["对待"]
  A --> D["变化"]

  B --> B1["有生"]
  B --> B2["有无生"]
  B --> B3["无生"]

  C --> C1["有对"]
  C --> C2["有无对"]
  C --> C3["无对"]

  D --> D1["有变"]
  D --> D2["有无变"]
  D --> D3["无变"]

  B -. "互含" .-> C
  C -. "互含" .-> D
  D -. "互含" .-> B

  E["有 / 有无 / 无"] -. "成圆" .-> A
```

## 学习路径

1. 先记住三条主线：生成、对待、变化。
2. 再把每条主线展开为三境：有、有无、无。
3. 用一个具体对象练习，比如一段关系、一个项目、一个念头。
4. 先问它如何生成，再问它如何对待，最后问它如何变化。
5. 回头检查：你是否把三者割裂了？能否在生成中看到对待和变化？
6. 最后把九境收回一个整体：不是为了分类，而是为了转变观察方式。

## 常见误区

{md_table(["误区", "更稳妥的理解"], [
    ["把九境当成九个固定等级", "九境是观察结构，不是僵硬阶梯。"],
    ["把无生、无对、无变理解成否定一切", "无不是抹掉现象，而是追到更深的根据。"],
    ["把三晳当成贴标签工具", "可以从工具入门，但目标是改变看事物的方式。"],
    ["只承认一种叫法", "化生、生成、流行、变化等口径有层次差异，不必互相否定。"],
    ["把有、有无、无讲成单向路线", "三者应回环理解，不是越往后越高级。"],
])}

## 自问自答练习

自问：我观察一件事时，只看到了“它发生了”，还缺什么？

自答：还要看它凭什么发生、与什么相待、会怎样变化。

自问：我说“无对”，是不是等于没有任何分别？

自答：不是。它不是取消分别，而是不被分别困住，还能说明分别如何成立。

自问：为什么三晳不能拆成三个孤立概念？

自答：因为生成、对待、变化彼此互含。只讲其中一个，若带不出另外两个，就还没有进入三晳的整体。

## 少量来源锚点

{md_table(["来源", "短摘句"], quote_rows)}

## 延伸阅读

- [概念总图](../learning/concept-map.md)
- [核心术语表](../terms/glossary.md)
- [学习路径](../learning/path.md)
- [资料总览](../sources/index.md)
"""


def build_review_report(records: list[dict[str, Any]]) -> str:
    high = sum(1 for record in records if record["confidence"] == "high")
    medium = sum(1 for record in records if record["confidence"] == "medium")
    low = sum(1 for record in records if record["confidence"] == "low")
    return f"""# 三晳九境专题评审报告

## 多 agent 输出

- Round 1 Agent A：证据索引，已归并为 `evidence.jsonl`。
- Round 1 Agent B：概念结构，已吸收进 `concept_graph.md` 与私版专题页。
- Round 1 Agent D：误区审查，已吸收进私版、公版误区段。
- Round 2 Agent C：课程化表达，已整理为 `teaching_lesson.md` 与 `qa_drills.md`。
- Round 2 Agent E：公开安全页，已整理为 `public_page.md`。
- Round 2 Agent F：质量评审，已用于降确定性、收口径、分私公。

## 证据统计

- high：{high}
- medium：{medium}
- low：{low}
- 总计：{len(records)}

## 主要修订决策

- 九境表可直接采用，但必须紧跟“不是九个孤立格子”的提醒。
- “有、有无、无”只作为讲解顺序，不写成线性台阶。
- “无生、无对、无变”不定义为终极断语，只说明不是简单否定。
- 化生/生成、流行/变化写成口径差异，不写成互相替代。
- 公版只保留 6 条短摘句，主体用白话编译。

## 公开安全检查

- `public_page.md` 不含 `## 全文`。
- `public_page.md` 不含本地全文路径。
- 短摘句 6 条。
- 同一来源短摘句不超过 2 条。
- 单条短摘句不超过 40 个汉字。

## 后续优化

- 下一轮可做“生中有对有变”的专题练习页。
- 再下一轮可把“生成/化生”和“变化/流行”的口径差异单独编成术语页。
- 全站优化应按专题推进，不宜一次性重写 66 篇。
"""


def validate_public_page(content: str) -> None:
    forbidden = ["## 全文", "corpus-fulltext", "output/knowledge/text", "output\\knowledge\\text", ".docx", ".pdf", ".doc"]
    for pattern in forbidden:
        if pattern in content:
            raise SystemExit(f"Public page contains forbidden pattern: {pattern}")
    if len(PUBLIC_QUOTES) > 6:
        raise SystemExit("Public quotes exceed the 6 quote limit")
    counts = Counter(source for source, _ in PUBLIC_QUOTES)
    for source, count in counts.items():
        if count > 2:
            raise SystemExit(f"Public source has too many quotes: {source}")
    for source, quote in PUBLIC_QUOTES:
        if len(quote) > 40:
            raise SystemExit(f"Public quote is too long ({source}): {quote}")


def compile_topic(topic: str) -> None:
    if topic != TOPIC_SLUG:
        raise SystemExit(f"Unsupported topic: {topic}")

    TOPIC_DIR.mkdir(parents=True, exist_ok=True)
    records = load_agent_evidence()
    validate_evidence(records)

    write_text(
        TOPIC_DIR / "evidence.jsonl",
        "\n".join(json.dumps(record, ensure_ascii=False) for record in records),
    )
    write_text(TOPIC_DIR / "source_map.md", build_source_map(records))
    write_text(TOPIC_DIR / "concept_graph.md", build_concept_graph())
    write_text(TOPIC_DIR / "teaching_lesson.md", build_teaching_lesson())
    write_text(TOPIC_DIR / "qa_drills.md", build_qa_drills())
    write_text(TOPIC_DIR / "private_dossier.md", build_private_dossier(records))

    public_page = build_public_page()
    validate_public_page(public_page)
    write_text(TOPIC_DIR / "public_page.md", public_page)
    write_text(TOPIC_DIR / "review_report.md", build_review_report(records))

    print(f"Compiled topic: {topic}")
    print(f"Output: {TOPIC_DIR}")
    print(f"Evidence rows: {len(records)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compile Sanxi topic outputs from multi-agent drafts.")
    parser.add_argument("--topic", default=TOPIC_SLUG, choices=[TOPIC_SLUG])
    args = parser.parse_args()
    compile_topic(args.topic)


if __name__ == "__main__":
    main()
