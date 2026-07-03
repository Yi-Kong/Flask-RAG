"""下载 BAAI/bge-small-zh-v1.5 模型到本地目录.

使用方法:
    # 直接下载（使用 Hugging Face 官方源）
    python download_model.py

    # 使用镜像站下载（国内推荐）
    HF_ENDPOINT=https://hf-mirror.com python download_model.py

    # 通过 .env 配置自定义模型名称:
    #   HF_MODEL_NAME=BAAI/bge-small-zh-v1.5
    #   EMBEDDING_MODEL=embedding_models/bge-small-zh-v1.5

模型会保存到项目目录下的 embedding_models/ 文件夹.
"""
import os
import sys

from dotenv import load_dotenv

# 加载 .env
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

# 模型名称和本地保存路径（从环境变量读取）
MODEL_NAME = os.getenv("HF_MODEL_NAME")
# 使用 EMBEDDING_MODEL 中的相对路径部分作为本地目录名
_embedding_path = os.getenv("EMBEDDING_MODEL")
if os.path.isabs(_embedding_path):
    LOCAL_DIR = _embedding_path
else:
    LOCAL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), _embedding_path)


def download_with_huggingface_hub():
    """使用 huggingface_hub 库下载模型（推荐，支持断点续传）."""
    from huggingface_hub import snapshot_download

    print(f"模型: {MODEL_NAME}")
    print(f"本地路径: {LOCAL_DIR}")
    print(f"HF_ENDPOINT: {os.environ.get('HF_ENDPOINT', '(默认官方源)')}")
    print("-" * 60)

    # 检查是否已下载
    config_file = os.path.join(LOCAL_DIR, "config.json")
    if os.path.exists(config_file):
        print("[✓] 模型已存在，无需重复下载")
        print(f"    路径: {LOCAL_DIR}")
        return True

    print("正在下载模型...（约 100MB，首次可能需要几分钟）")
    try:
        snapshot_download(
            repo_id=MODEL_NAME,
            local_dir=LOCAL_DIR,
            local_dir_use_symlinks=False,  # Windows 兼容
            resume_download=True,           # 断点续传
        )
        print(f"\n[✓] 下载完成！模型已保存到: {LOCAL_DIR}")
        return True
    except Exception as e:
        print(f"\n[✗] 下载失败: {e}", file=sys.stderr)
        print("\n请尝试以下方法之一：", file=sys.stderr)
        print("  1. 使用镜像站: HF_ENDPOINT=https://hf-mirror.com python download_model.py")
        print("  2. 确保网络能访问 Hugging Face")
        print("  3. 手动下载后放到:", LOCAL_DIR)
        return False


def download_with_sentence_transformers():
    """备选方案：使用 sentence-transformers 库下载.

    这个方法会触发模型加载和下载，下载后自动缓存到本地。
    然后我们手动复制到项目的 models 目录下。
    """
    from sentence_transformers import SentenceTransformer

    print("备选方案：通过 sentence-transformers 加载模型触发下载...")
    print("模型会被下载到 Hugging Face 缓存目录，然后复制到项目本地。")
    print("-" * 60)

    try:
        model = SentenceTransformer(MODEL_NAME)
        # 获取模型在缓存中的实际路径
        cache_dir = model._modules["0"].auto_model.config._name_or_path
        print(f"\n模型已缓存到系统目录")
        print(f"输出维度: {model.get_sentence_embedding_dimension()}")

        # 尝试找到实际文件路径
        import shutil
        from sentence_transformers.util import snapshot_download as st_snapshot

        # 直接从模型配置获取路径
        model_path = model._first_module().get_config_dict().get("_name_or_path", "")

        print(f"模型源路径: {model_path}")
        if os.path.isdir(model_path) and model_path != MODEL_NAME:
            if not os.path.exists(LOCAL_DIR):
                shutil.copytree(model_path, LOCAL_DIR)
                print(f"[✓] 模型已复制到: {LOCAL_DIR}")
            return True
        else:
            print("[!] 无法确定缓存路径，但模型已下载到系统缓存中")
            print(f"    可以通过 Hugging Face 缓存目录找到模型文件")
            return True
    except Exception as e:
        print(f"[✗] 下载失败: {e}", file=sys.stderr)
        return False


def verify_model():
    """验证下载的模型是否可用."""
    from sentence_transformers import SentenceTransformer

    print("\n" + "=" * 60)
    print("验证模型可用性...")
    print("-" * 60)

    try:
        model = SentenceTransformer(LOCAL_DIR)
        dim = model.get_sentence_embedding_dimension()
        print(f"[✓] 模型加载成功!")
        print(f"    路径: {LOCAL_DIR}")
        print(f"    输出维度: {dim}")

        # 测试编码
        test_embedding = model.encode(["测试文本"], normalize_embeddings=True)
        print(f"    编码测试: shape={test_embedding.shape}, dtype={test_embedding.dtype}")
        print(f"\n模型完全可用！")
        return True
    except Exception as e:
        print(f"[✗] 验证失败: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    os.makedirs(os.path.dirname(LOCAL_DIR), exist_ok=True)

    # 方法 1: 使用 huggingface_hub 直接下载到项目目录
    success = download_with_huggingface_hub()

    if not success:
        # 方法 2: 备选方案
        print("\n尝试备选下载方案...")
        success = download_with_sentence_transformers()

    if success:
        verify_model()
    else:
        print("\n" + "=" * 60)
        print("手动下载说明：")
        print(f"1. 在有网络的机器上运行: git clone https://huggingface.co/{MODEL_NAME}")
        print(f"2. 或访问 https://huggingface.co/{MODEL_NAME} 下载所有文件")
        print(f"3. 将所有文件复制到: {LOCAL_DIR}")
        print(f"4. 确保目录下包含 config.json, pytorch_model.bin (或 model.safetensors), tokenizer.json 等文件")
        sys.exit(1)
