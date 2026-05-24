from collections import defaultdict


def gnn_risk(edges):
    graph = defaultdict(set)
    user_degree = defaultdict(int)
    merchant_degree = defaultdict(int)

    for edge in edges:
        user = edge.get("user")
        merchant = edge.get("merchant")

        if not user or not merchant:
            continue

        graph[user].add(merchant)
        graph[merchant].add(user)
        user_degree[user] += 1
        merchant_degree[merchant] += 1

    suspicious_nodes = []

    for node, neighbors in graph.items():
        degree = len(neighbors)
        repeated_connections = user_degree.get(node, 0) if node in user_degree else merchant_degree.get(node, 0)

        if degree >= 2 or repeated_connections >= 2:
            suspicious_nodes.append(
                {
                    "node": node,
                    "degree": degree,
                    "connections": sorted(neighbors),
                    "reason": (
                        "Repeated payment pattern"
                        if repeated_connections >= 2 and degree <= 1
                        else "Highly connected transaction node"
                    ),
                }
            )

    suspicious_nodes.sort(key=lambda item: (item["degree"], len(item["connections"])), reverse=True)
    return suspicious_nodes