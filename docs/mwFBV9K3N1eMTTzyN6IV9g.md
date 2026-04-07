# mwFBV9K3N1eMTTzyN6IV9g

> 来源: https://mp.weixin.qq.com/s/mwFBV9K3N1eMTTzyN6IV9g
> 爬取时间: 2026-04-06T19:15:23.701724



以前你想处理邮件，得打开邮箱软件，一个个点、一个个回。

以后在聊天软件里跟 AI 说一句把今天重要的邮件处理一下，它就帮你干了。

这带来一个连锁反应：**软件以后不是给人设计的，是给 AI 设计的。**

但问题来了——AI 想帮你操作 Gmail、Drive、日历，你得先给它开个后门。

自己去调 API 太折腾了，用各家 SDK 又不统一。

就在这个节点，**Google 放出了一个实验性质的项目** 。

**谷歌推出了一个开源项目 Google Workspace CLI** （命令名 `gws`）。

它即是给人设计的，更是给 AI Agent 设计的。

  * 

    
    
     GitHub 地址：https://github.com/googleworkspace/cli

它覆盖所有 Google Workspace 服务，Drive、Gmail、Calendar、Sheets、Docs、Chat 等。

支持什么，它就能用什么。来看几个几个实际例子：

  *   *   *   *   *   *   *   *   *   *   * 

    
    
    # 列出最近的 10 个文件gws drive files list --params '{"pageSize": 10}'# 创建一个 Google 表格gws sheets spreadsheets create --json '{"properties":{"title":"Q1 Budget"}}'# 在 Google Chat 发消息gws chat spaces.messages.create \--params '{"parent":"spaces/xyz"}' \--json '{"text":"Deploy complete."}' \--dry-run# 查看某个 API 的参数结构（调试神器）gws schema drive.files.list

它有个很聪明的设计，**不内置固定的命令表** 。

每次运行时，它会从 Google 官方拉取最新的 API 定义，动态构建命令。Google 一旦给某个服务加了新功能，你立刻就能用，不用等 CLI 升级。

02为 AI Agent 量身定做

## 历史真是一个循环呀，没想现在命令行这种产品形态又火了：  

## 命令行将复杂的系统交互简化为了纯粹的结构化文本流，使 AI Agent 能够以其原生的 Token 预测方式直接驱动任务。

## 彻底消除了图形界面（GUI）带来的视觉解析成本与交互不确定性。

## 这个谷歌开源的命令行工具真是为 AI Agent 量身定做的。

### 首先，它所有输出都是 JSON

LLM 最怕非结构化文本。`gws` 的设计哲学是：**一切皆 JSON，** 响应体、元数据、错误信息，全部结构化。

AI Agent 不需要解析人类视角的输出，直接读 JSON 就行。

### 加自带 100+ Agent Skills，有的 Skill 和单个 API 方法一一对应。

### 有的封装了 Gmail 批量操作、Drive 文档整理、Sheets 数据批处理等

LLM 不需要自己拼 API 调用，直接调用这些技能就行。

03五分钟快速上手
    
    
    你可以通过下面这些命令开始玩一下这个命令行工具。  
    

  *   *   *   *   *   *   *   *   *   *   *   * 

    
    
    # 1. 安装npm install-g @googleworkspace/cli  
    # 2. 认证gws auth setupgws auth login  
    # 3. 试一下gws drive files list --params'{"pageSize":5}'  
    # 4. 查参数gws schema drive.files.list
    
    
    除此之外，直接对接 OpenClaw 和 Gemini CLI

  *   *   *   *   *   * 

    
    
    # OpenClaw 一键安装ln -s $(pwd)/skills/gws-* ~/.openclaw/skills/  
    # Gemini CLI 扩展gemini extensions install https://github.com/googleworkspace/cli  
    
    
    
    装完就能让这些 AI 助理直接操作你的 Workspace。

如果你在做 AI 助理能操作 Gmail / Drive / Docs 的产品，这个 CLI 就是一个**现成的 Workspace 能力网关** 。

更大的意义是它代表了一个趋势：**大厂开始主动拥抱 Agent 时代，把自家产品 Agent-ready 化** 。

未来，每个 SaaS 都需要回答一个问题：如果用户只通过 AI Agent 与我交互，我的产品该长什么样？

Google Workspace CLI，给了我们一个答案。

04

**点击下方卡片，关注逛逛 GitHub**

这个公众号历史发布过很多有趣的开源项目，如果你懒得翻文章一个个找，你直接关注微信公众号：逛逛 GitHub ，后台对话聊天就行了：

