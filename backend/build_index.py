# © 2026 BUPT_Mint-Green
# All rights reserved.

from backend.data_loader import load_ccpc, load_fspc, load_pqed
from backend.retrieval.vector_store import VectorPoetryStore


def main():
    store = VectorPoetryStore()
    if not store.available:
        raise RuntimeError(f"无法初始化向量模型：{store.reason}")
    datasets = {"ccpc": load_ccpc(), "fspc": load_fspc(), "pqed": load_pqed()}
    for name, records in datasets.items():
        print(f"正在构建 {name}：{len(records)} 条")
        print(f"{name} 已入库：{store.build(name, records)} 条")
    print(store.status())


if __name__ == "__main__":
    main()
