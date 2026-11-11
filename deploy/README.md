# Deploy / 部署

**Quickest (Tag build, one 80 GB GPU) / 最快（Tag 版，一张 80 GB 显卡）:**

```bash
pip install "sophon-realtime[trt]"   # Python 3.12, Linux, CUDA 13; keep [trt]: without TensorRT the voice is ~3x slower under load / 一定要带 [trt]，否则高并发下慢约 3 倍
sophon-realtime serve           # downloads Sophon-Realtime-32B-Tag (~42 GB) on first run, serves on port 8000 / 首次运行会自动下载权重
```

Endpoints / 接口: `ws://HOST:8000/v1/realtime` (full duplex / 全双工) · `POST /v1/chat/completions`.

More / 更多:
- One-command scripts with an isolated environment / 一键脚本（独立虚拟环境）: [Tag](../tag/README.md) · [Flash](../flash/README.md)
- Live mode (OpenAI GPT-Live compatible) / Live 模式（兼容 OpenAI GPT-Live）: [live/](../live/README.md)
- E2E build (one 80 GB GPU, own engine) / E2E 版（一张 80 GB 显卡，自研引擎）: [docs/deploy.md](../docs/deploy.md)
