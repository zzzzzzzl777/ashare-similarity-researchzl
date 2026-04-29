## Summary

- 

## Scope Check

- 为什么这个改动与当前项目相关：
- 明确不处理的范围：

## Validation

- [ ] `python -m pytest -q`
- [ ] `python -m ashare_similarity.cli doctor`
- [ ] 如果改动影响 Web，已本地验证首页 / `/api/search` / `/api/status` / 导出
- [ ] 如果改动影响数据、索引或维护链路，已补充相关 `status` / CLI 输出或说明

## Data Boundary

- [ ] 没有提交 `data/`、`*.duckdb`、导出文件、日志或其他本地缓存工件
- [ ] 粘贴到 PR 描述里的 `doctor` / `status` 输出已检查本地路径、IP、代理/VPN 信息

## Notes

- 是否影响数据格式、CLI、索引、免费数据回填链路或 GPU/加速状态：
- 风险、兼容性或后续待办：
