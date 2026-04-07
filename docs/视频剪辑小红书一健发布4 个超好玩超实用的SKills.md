# 视频剪辑、小红书一健发布，4 个超好玩，超实用的SKills

> 来源: https://mp.weixin.qq.com/s/8gwm9z87Aqh-cabmbYwQNQ
> 爬取时间: 2026-04-07T20:03:19.843879


面向小红书内容创作者的全链路自动化工具，可完成文案生成、图片渲染到平台发布的全流程操作。该工具最早在linux.do社区流出，当前Star量较低，属于小众实用型工具。

核心功能基于Playwright浏览器自动化框架实现，可直接将Markdown格式文本渲染为平台适配的笔记图片，支持自定义渐变背景、封面样式等视觉参数，发布链路已完成官方接口适配，可实现一键推送上线。

提供Python、Node.js两种脚本实现方案，使用者可根据自身技术栈灵活选择。

  * 

    
    
      开源地址：https://github.com/comeonzhj/Auto-Redbook-Skills

## 02 AI文本去味Skill

针对AI生成文本的同质化、模板化问题开发的改写工具，是Humanizer项目的中文优化版本，底层对齐维基百科公开的AI写作特征数据库，可精准识别并消除AI生成痕迹。

内置多维度检测逻辑，覆盖内容逻辑、语法结构、表达风格、交互模式四个检测维度，可定位AI特有的表述习惯并完成自然化改写，改写后的文本符合原生中文写作逻辑。

### 使用步骤

执行克隆命令拉取项目文件：

  * 

    
    
      git clone https://github.com/op7418/Humanizer-zh.git ~/.claude/skills/humanizer-zh

  

重启Claude Code或手动重载skills目录后，输入/humanizer-zh即可激活工具，直接输入待处理文本即可完成改写。

  * 

    
    
      开源地址：https://github.com/op7418/Humanizer-zh

  

## 03 智能视频剪辑Skill

videocut-skills是专门面向口播类视频创作者的开源剪辑工具，可自动识别视频中的口误、静音片段、冗余语气词，仅需简单指令即可驱动AI完成全流程剪辑操作。

字幕生成模块基于OpenAI Whisper模型实现，支持自定义词典完成专业词汇纠错，剪辑底层采用FFmpeg框架处理音视频流，兼顾处理速度与输出质量，工具内置用户习惯学习逻辑，可根据历史操作动态优化剪辑规则。

口播类创作者无需掌握专业剪辑软件操作，从环境部署到成片输出全流程均可通过对话框命令完成，平均剪辑效率提升70%以上。

### 使用步骤

将项目克隆到Claude Code的skills目录：

  * 

    
    
      git clone https://github.com/Ceeon/videocut-skills.git ~/.claude/skills/videocut

  

打开Claude Code，输入/videocut:安装指令，AI将自动完成依赖安装与模型下载（模型包约5GB），部署完成后即可导入素材开始剪辑。

  * 

    
    
      开源地址：https://github.com/Ceeon/videocut-skills

## 04 Skill批量安装工具

add-skill并非单一功能Skill，是Vercel Labs推出的命令行工具，可实现第三方Skill向Claude Code、Codex、Cursor等平台的一键安装。

工具可直接从GitHub仓库提取Skill配置文件，自动识别仓库内的标准化部署文件完成环境配置，无需手动复制粘贴文件或修改配置项，全程仅需一行命令即可完成部署。

  * 

    
    
      开源地址：https://github.com/vercel-labs/add-skill
