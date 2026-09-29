# 特种设备点检运维平台

面向锅炉、压力容器、起重机械、电梯等特种设备的台账建档、日常点检、润滑保养、定期检验与隐患整改的一体化运维后台。

这是一个前后端分离的管理平台：前端 Vue 3 + Vite + TypeScript，后端 FastAPI（Python）。
两边各自独立启动，前端 dev server 已关掉自动打开页面，启动后按终端打印的地址手工打开。

## 目录结构

```text
.
├── frontend/                 Vue 3 + Vite + TypeScript 前端
│   ├── src/views/            每个业务模块一个页面
│   ├── src/api/              统一请求封装
│   ├── src/stores/           会话与筛选状态
│   ├── package-lock.json     前端依赖锁定文件（npm ci 按它安装）
│   └── vite.config.ts        dev server 配置（open: false，端口走环境变量）
├── backend/                  FastAPI（Python） 后端
│   ├── app/routers/          每个业务模块一组接口
│   ├── app/services/         业务规则与状态流转
│   ├── app/seed.py           示例数据装载/校验（幂等，可重复执行）
│   ├── app/store.py          内存数据仓库
│   ├── data/seed.json        示例数据唯一来源（含模块、检验类别、检验机构）
│   ├── requirements.txt      直接依赖（版本锁定）
│   ├── requirements.lock.txt 全部依赖锁定（构建以此为准）
│   └── scripts/setup.sh      分步构建：环境检查→venv→依赖→数据自检
├── .env.example              环境变量与端口的准星配置（复制为 .env 使用）
└── docker-compose.yml
```

## 可重复构建（一条命令）

```bash
make install      # = 后端 setup.sh + 前端 npm ci，每一步都可单独重跑
```

构建分四步，任意一步失败都会打印**卡在哪一步、原因和重试办法**，修正后重跑同一条命令即可，
不会装出半成品：

1. 检查 Python（需 3.10+，缺 `venv` 时自动用 get-pip.py 引导）；
2. 准备 `.venv`（已存在则跳过，删掉可强制重建）；
3. 按 `backend/requirements.lock.txt` 安装后端依赖（pip 幂等，版本与 lock 完全一致）；
   前端按 `frontend/package-lock.json` 执行 `npm ci`（有 lock 才允许安装）；
4. 校验 `data/seed.json`，并做一次“连续装载两遍”的幂等自检。

单独执行：`make install-backend`、`make install-frontend`、`make seed`、`make verify`。

## 环境变量与端口

所有端口、主机、代理目标都以根目录 `.env.example` 这份配置为准，换环境只改环境变量不改代码：

| 变量 | 默认值 | 说明 |
| --- | --- | --- |
| `APP_HOST` / `APP_PORT` | `127.0.0.1` / `8000` | 后端监听地址；容器里用 `APP_HOST=0.0.0.0` |
| `APP_SEED_FILE` | `data/seed.json` | 示例数据文件路径（本地与镜像是同一份） |
| `APP_SEED_ON_STARTUP` | `true` | 启动时是否自检并幂等装载基础数据 |
| `APP_ALLOWED_ORIGINS` | 两个 5173 来源 | CORS 白名单，逗号分隔 |
| `VITE_DEV_HOST` / `VITE_DEV_PORT` | `127.0.0.1` / `5173` | 前端 dev server（strictPort，占用即失败） |
| `VITE_PROXY_TARGET` | `http://127.0.0.1:8000` | `/api` 代理目标，容器内指向 `http://backend:8000` |

非法端口/布尔值会在启动时直接报清楚，例如
`环境变量 APP_PORT='abc' 不是合法端口，应为 1-65535 的整数`。

## 基础数据（示例数据）

- 唯一来源是 `backend/data/seed.json`：模块清单、模块中文名、检验类别、检验机构、各表示例行都在这里，
  本地开发与镜像构建读同一份，**列表、健康检查、运营概览看到的数据完全一致**。
- 装载按「模块 + id」去重，`make seed`、容器重启、再次构建都**不会产生重复记录**。
- 镜像在**构建期**执行一次 `python -m app.seed verify`，数据文件缺失/损坏/引用了不存在的检验类别时
  直接让构建失败；容器**启动时**再幂等执行一次 `init`。
- 定期检验的基础数据接口：
  - `GET /api/inspect/categories` 检验类别（年度检验、全面检验、定期自行检查）
  - `GET /api/inspect/agencies` 检验机构
  - `GET /api/inspect?category=年度检验` 可按检验类别过滤
- 运营概览的“业务模块”卡片数取自 `seed.json` 里声明的模块数（当前 18），不再由前端硬编码。

## 启动

### 后端

```bash
cd backend
./run.sh          # 等价于 make backend；首次没有 .venv 时会自动跑 scripts/setup.sh
```

健康检查：`curl http://127.0.0.1:8000/api/health`，返回里能看到 `modules`、
`inspect_categories`、`inspect_agencies` 计数。

### 前端

```bash
cd frontend
npm run dev       # 等价于 make frontend
```

前端默认监听 `http://127.0.0.1:5173/`，dev server 不会自动打开浏览器，
需要自己访问。`/api` 由 vite 代理到后端（`VITE_PROXY_TARGET`）。

### Docker

```bash
docker compose up --build
```

依赖按 lock 文件安装，基础数据在构建期校验、容器启动时幂等初始化。

## 业务模块

| 模块 | 目录 | 业务对象 | 主要字段 |
| --- | --- | --- | --- |
| 锅炉设备 | `boiler` | 锅炉设备 | 设备编号、设备名称、额定蒸发量 |
| 压力容器 | `vessel` | 压力容器 | 容器编号、容器名称、设计压力 |
| 压力管道 | `pressurepipe` | 压力管道 | 管道编号、管道名称、管道级别 |
| 起重机械 | `crane` | 起重机械 | 机械编号、机械名称、额定起重量 |
| 电梯设备 | `elevator` | 电梯设备 | 电梯编号、电梯名称、载重规格 |
| 场内机动车辆 | `forklift` | 场内机动车辆 | 车辆编号、车辆名称、动力方式 |
| 点检计划 | `plan` | 点检计划 | 计划编号、点检对象、点检周期 |
| 点检记录 | `spotcheck` | 点检记录 | 点检单号、关联计划、点检设备 |
| 润滑保养 | `lubricate` | 保养记录 | 保养单号、保养设备、润滑点位 |
| 定期检验 | `inspect` | 检验任务 | 检验编号、检验对象、检验类别 |
| 检验报告 | `report` | 检验报告 | 报告编号、关联检验、报告类别 |
| 隐患登记 | `hazard` | 隐患记录 | 隐患编号、涉及设备、隐患类型 |
| 整改闭环 | `rectify` | 整改单 | 整改单号、关联隐患、整改措施 |
| 使用登记 | `register` | 登记记录 | 登记编号、登记设备、使用单位 |
| 作业人员 | `operator` | 作业人员 | 人员编号、人员姓名、所属单位 |
| 备件器材 | `spare` | 备件器材 | 备件编号、备件名称、适用设备 |
| 维保合同 | `contract` | 维保合同 | 合同编号、服务单位、维保设备 |
| 费用结算 | `settle` | 结算单 | 结算单号、关联合同、费用类别 |

## 约定

- 每个模块的前端页面在 `frontend/src/views/<模块>/index.vue`，后端接口在
  `backend/app/routers/<模块>.py`，业务规则在 `backend/app/services/<模块>.py`。
- 列表接口统一返回 `{ items, total, page, size }`，动作接口统一返回 `{ ok, message }`。
- 状态流转只允许在 `app/services` 里改，路由层不做业务判断。
