#set document(
  title: "同人誌タイトル",
  author: "著者名",
)

#set page(
  paper: "jis-b5",
  margin: (top: 20mm, bottom: 20mm, inside: 22mm, outside: 18mm),
  numbering: "1",
)

#set text(
  font: ("Hiragino Mincho ProN"),
  size: 8pt,
  lang: "ja",
)

#set par(
  leading: 0.8em,
  first-line-indent: 1em,
  justify: true,
)

#set heading(numbering: "1.1")

// 見出しサイズを階層ごとに明確に差をつける
#show heading.where(level: 1): set text(size: 15pt)
#show heading.where(level: 2): set text(size: 12pt)
#show heading.where(level: 3): set text(size: 10pt)
#show heading.where(level: 4): set text(size: 9pt)
#show heading.where(level: 5): set text(size: 7.5pt, style: "italic")

// 表紙
#align(center + horizon)[
  #text(size: 24pt, weight: "bold")[同人誌タイトル]

  #v(2em)

  #text(size: 14pt)[著者名]

  #v(1em)

  #text(size: 12pt)[2026年 夏コミ]
]

#pagebreak()

// 目次
#outline(title: "目次", depth: 3)

#pagebreak()

// 本文
= はじめに

ここに本文を書いていきます。

= 運用

// 共通の戦略説明
#include "strategy.typ"

// 週次レポート（新しい週を上、過去週を下に並べる）
#include "week2.typ"
#include "week1.typ"

= おわりに

あとがきをここに書きます。
