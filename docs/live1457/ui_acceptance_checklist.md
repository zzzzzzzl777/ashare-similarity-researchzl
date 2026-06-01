# 14:57 实时候选操作台 UI 验收清单

日期：2026-05-11
版本：v1.0

## 1. 功能验收

- [ ] 页面清楚区分 formal、postclose、test 三种模式
- [ ] formal invalid 时不展示可参考候选
- [ ] postclose 结果标记为"收盘验证"
- [ ] test 结果标记为"测试诊断"
- [ ] 候选表可显示
- [ ] 全量概率前列可显示（默认折叠）
- [ ] 运行日志可查看（底部折叠抽屉）
- [ ] artifact 路径可显示、可复制
- [ ] 点击候选行打开 Inspector 查看详情
- [ ] stop 按钮能停止当前模式任务
- [ ] 按钮时间控制正确：正式跑 14:57 后、收盘验证 15:00 后、测试跑随时

## 2. 数据可信度验收

- [ ] 显示 run_id
- [ ] 显示模型 bundle 特征数
- [ ] 显示 snapshot 状态和 quote_time
- [ ] 显示 14:30 cache 状态
- [ ] 显示 output_grade
- [ ] 显示 formal_valid 和原因
- [ ] formal 结果必须 is_formal_valid=true 才显示为正式候选
- [ ] postclose 显示 is_postclose_complete 和原因
- [ ] test 显示近似警告

## 3. 视觉验收

- [ ] 首屏有明确产品身份（标题、模型、状态）
- [ ] 无临时脚本页面感
- [ ] 表格密集但可读
- [ ] formal 使用绿色系
- [ ] postclose 使用琥珀色系
- [ ] test 使用灰色系
- [ ] failed 使用红色
- [ ] 日志默认折叠，不抢主视觉
- [ ] 候选表固定表头

## 4. 状态展示验收

- [ ] formal valid → 绿色 "正式候选有效"
- [ ] formal invalid → 红色 "正式候选无效"
- [ ] formal idle → 灰色 "等待运行"
- [ ] formal running → 蓝色 "正在运行"
- [ ] postclose completed → 琥珀色 "收盘验证完成"
- [ ] test completed → 灰色 "测试诊断完成"
- [ ] failed → 红色 "运行失败"

## 5. 布局验收

- [ ] 顶部状态栏固定
- [ ] 左侧控制栏 ~300px
- [ ] 主工作区弹性宽度
- [ ] 右侧 Inspector 可折叠 ~360px
- [ ] 底部诊断抽屉可展开/折叠
- [ ] 1440x900 首屏不混乱
- [ ] 1920x1080 信息密度合理

## 6. 交互验收

- [ ] Tab 切换 formal/postclose/test
- [ ] 候选表行可点击打开 Inspector
- [ ] 底部抽屉可展开查看日志
- [ ] Artifact 路径可复制
- [ ] 全量概率表可展开/折叠
- [ ] 按钮 loading 防重复点击
- [ ] 运行时自动刷新（2s 轮询）

## 7. 安全边界验收

- [ ] formal 模式不会补 0 或回退
- [ ] postclose 不会被标记为正式候选
- [ ] test 明确标注近似警告
- [ ] P0 特征检查展示在控制栏
- [ ] Readiness checklist 显示数据准备状态
