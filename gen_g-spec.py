import re

def parse_gspec(lines):
    """
    単一の G-spec ブロック（実行/分岐/--- を含む行群）から edges を生成する。
    """
    edges = []
    current = None  # 現在のストリームの末尾ノード（ラベル）

    for raw in lines:
        line = raw.rstrip("\n")
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        # ストリーム切り替え ---
        if stripped.startswith("---"):
            current = None
            continue

        # 実行 X
        if stripped.startswith("実行"):
            # 先頭の「実行」を取り除いて残りをノード名とみなす
            node = stripped[len("実行"):].strip()

            # 直列遷移（current があり、かつ自己ループでない場合だけ）
            if current and current != node:
                edges.append((current, "", node))

            current = node
            continue

        # 分岐 |条件| X  or  分岐 ｜条件｜X
        if stripped.startswith("分岐"):
            body = stripped[len("分岐"):].strip()
            # 半角 | と 全角 ｜ のどちらにもマッチさせる
            m = re.search(r"[|｜](.+?)[|｜](.+)", body)
            if m:
                cond = m.group(1).strip()
                node = m.group(2).strip()
                # current から node へのラベル付き遷移
                if current:
                    edges.append((current, cond, node))
            continue

    return edges


def build_node_ids(edges):
    """
    日本語ラベル → 安全なノードID（n0, n1, …）の対応表を作る
    （ブロックごとに独立して使う）
    """
    mapping = {}
    for src, _, dst in edges:
        for name in (src, dst):
            if name not in mapping:
                mapping[name] = f"n{len(mapping)}"
    return mapping


def mermaid_block_from_edges(edges):
    """
    単一の edges から 1 つの ```mermaid ブロック文字列を生成する。
    """
    if not edges:
        return ""

    node_ids = build_node_ids(edges)

    out = []
    out.append("```mermaid")
    out.append("flowchart TD")

    # ノード定義（ID とラベル）
    for label, nid in node_ids.items():
        safe_label = label.replace('"', r'\"')
        out.append(f'    {nid}["{safe_label}"]')

    # エッジ定義
    for src, cond, dst in edges:
        sid = node_ids[src]
        did = node_ids[dst]
        if cond:
            out.append(f"    {sid} -->|{cond}| {did}")
        else:
            out.append(f"    {sid} --> {did}")

    out.append("```")
    return "\n".join(out)


def parse_segments(lines):
    """
    gspec.txt 全体を、順番を保ったセグメント列に分解する。

    セグメントの種類:
      - {"type": "markdown", "text": "..."}
      - {"type": "gspec",    "lines": [...]}
    """
    segments = []

    in_md_block = False
    current_md = []
    current_gspec = []

    for raw in lines:
        line = raw.rstrip("\n")

        # ```md 開始
        if not in_md_block and line.strip().startswith("```md"):
            # 直前までに G-spec 行が溜まっていたら一旦閉じる
            if current_gspec:
                segments.append({"type": "gspec", "lines": current_gspec})
                current_gspec = []
            in_md_block = True
            current_md = []
            continue

        # ``` 終了（Markdown ブロック終わり）
        if in_md_block and line.strip().startswith("```"):
            in_md_block = False
            segments.append({"type": "markdown", "text": "\n".join(current_md)})
            current_md = []
            continue

        # Markdown ブロック内
        if in_md_block:
            current_md.append(line)
            continue

        # それ以外は G-spec 側にまわす（空行やコメントも含めて保持）
        current_gspec.append(line)

    # ファイル末尾で G-spec が残っていたらセグメントにする
    if current_gspec:
        segments.append({"type": "gspec", "lines": current_gspec})

    return segments


def convert_file(lines):
    """
    gspec.txt 全体を読み、Markdown と Mermaid を交互に並べた .md テキストを返す。
    """
    segments = parse_segments(lines)
    out_lines = []

    for seg in segments:
        if seg["type"] == "markdown":
            text = seg["text"]
            if text.strip():
                out_lines.append(text.strip())
        elif seg["type"] == "gspec":
            edges = parse_gspec(seg["lines"])
            block = mermaid_block_from_edges(edges)
            if block:
                out_lines.append(block)

        # セグメント間は空行で区切る
        if out_lines and not out_lines[-1].endswith("\n"):
            out_lines.append("")

    # 末尾の空行を調整
    result = "\n".join(l for l in out_lines if l is not None)
    return result.strip() + "\n"


if __name__ == "__main__":
    with open("gspec.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()

    markdown = convert_file(lines)

    with open("flowchart.md", "w", encoding="utf-8") as f:
        f.write(markdown)

    print("flowchart.md を生成しました。")
