# Deploy / 部署

**Quickest (Tag build, one 80 GB GPU) / 最快（Tag 版，一张 80 GB 显卡）:**

```bash
pip install sophon-realtime     # Python 3.12, Linux, CUDA
sophon-realtime serve           # downloads Sophon-Realtime-32B-Tag (~42 GB) on first run, serves on port 8000 / 首次运行会自动下载权重
```

Endpoints / 接口: `ws://HOST:8000/v1/realtime` (full duplex / 全双工) · `POST /v1/chat/completions`.

More / 更多:
- One-command scripts with an isolated environment / 一键脚本（独立虚拟环境）: [Tag](../tag/README.md) · [Flash](../flash/README.md)
- Live mode (OpenAI GPT-Live compatible) / Live 模式（兼容 OpenAI GPT-Live）: [live/](../live/README.md)
- E2E research preview (two GPUs) / E2E 研究预览（两张卡）: [docs/deploy.md](../docs/deploy.md)
