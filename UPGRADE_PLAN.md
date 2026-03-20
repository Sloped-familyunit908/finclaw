# finclaw 升级质量保证方案

## 基线 (2026-03-20 04:55 UTC)
- Git: fb91a29
- Tests: **3934 passed**, 0 failed (--ignore=examples)
- Python: 3.12.10
- 命令: `& "C:\Users\kazhou\AppData\Local\Programs\Python\Python312\python.exe" -m pytest --ignore=examples --tb=no -q`

## 质量红线
1. **每次commit前必须跑全量测试，3934+ passed, 0 failed**
2. **不删除任何现有功能代码，只重组/整合**
3. **cn_scanner 回测结果不能regression** — 核心赚钱模块
4. **UI升级后必须浏览器实际查看，截图确认**
5. **每个改动独立commit，方便回滚**

## 升级清单

### Phase 1: 模块整合 (不改功能，只整理结构)
- [ ] backtest + backtesting → backtesting
- [ ] exchange + exchanges → exchanges  
- [ ] strategy + strategies → strategies
- [ ] plugins + plugin_system → plugins
- [ ] 清理空/重复__init__.py
- [ ] 每步跑测试确认

### Phase 2: 代码质量
- [ ] 清理dead code (COMPETITIVE_ANALYSIS已标记的)
- [ ] import整理
- [ ] type hints补全
- [ ] docstring补全

### Phase 3: UI实际验证
- [ ] npm run build
- [ ] npm run dev → 浏览器截图每个tab
- [ ] 检查数据显示是否合理
- [ ] 移动端适配检查

### Phase 4: 文档+发布
- [ ] PyPI dry-run
- [ ] README更新
- [ ] CHANGELOG更新
