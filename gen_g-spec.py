import re

def parse_gspec(lines):
    edges = []
    current = None  # 現在のストリームの末尾ノード（ラベル）

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue

        # ストリーム切り替え ---
        if line.startswith("---"):
            current = None
            continue

        # 実行 X
        if line.startswith("実行"):
            # 先頭の「実行」を取り除いて残りをノード名とみなす
            node = line[len("実行"):].strip()

            # 直列遷移（current があり、かつ自己ループでない場合だけ）
            if current and current != node:
                edges.append((current, "", node))

            current = node
            continue

        # 分岐 |条件| X  or  分岐 ｜条件｜X
        if line.startswith("分岐"):
            body = line[len("分岐"):].strip()
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
    """日本語ラベル → 安全なノードID（n0, n1, …）の対応表を作る"""
    mapping = {}
    for src, _, dst in edges:
        for name in (src, dst):
            if name not in mapping:
                mapping[name] = f"n{len(mapping)}"
    return mapping


def to_mermaid(edges):
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


if __name__ == "__main__":
    with open("gspec.txt", "r", encoding="utf-8") as f:
        lines = f.readlines()

    edges = parse_gspec(lines)
    mermaid = to_mermaid(edges)

    with open("flowchart.md", "w", encoding="utf-8") as f:
        f.write(mermaid)

    print("flowchart.md を生成しました。")
