# 1.ScreenBox——高颜值开源播放器，可以完全替代PotPlayer

> 来源: https://mp.weixin.qq.com/s/QKAUV0c0qrsEr64HeQo73g
> 爬取时间: 2026-04-06T15:44:31.448535


#   

  

  

GitHub上每天都会出现很多新项目，有些很小众，但功能却非常有意思。github上的热门开源项目，但真正对于大多数普通人来说，功能好用、界面简洁是最重要的。

  

  

## 1.ScreenBox——高颜值开源播放器，可以完全替代PotPlayer

  

开源项目：  
http://github.com/huynhsontung/Screenbox

很多人电脑里还躺着**PotPlayer** 。功能强，但界面老气，设置复杂，新手打开就头大。

ScreenBox的第一感觉是**干净** 。

Win11**原生风格** ，没有多余按钮。

  

  

打开视频，界面几乎贴着系统设计语言走，**看着就舒服** 。

它底层基于LibVLCSharp，稳定性不用担心。常见格式基本全吃。

关键是**开源、无广告、安装简** 单，不会弹出莫名其妙的消息。

操作也直观。拖进文件就能播，快捷键顺手，倍速、字幕切换都在显眼位置。哪怕小白都能很快上手。

## 二、RuView——用WiFi“看见”墙后的人

RuView 是一个基于 WiFi 信号实现人体感知的开源项目，可用于识别人体动作、姿态甚至生命体征，无需摄像头或穿戴设备。

项目地址：https://github.com/ruvnet/RuView

这个项目最吸引人的地方只有一句话：**用WiFi信号** 识别人类动作。

RuView的核心思路是分析WiFi信号的变化，从中提取人体运动信息。

它**不依赖摄像头** ，也不需要穿戴设备，只利用无线电信号就能识别人体动作、存在状态甚至生命体征。

  

  

简单理解就是：**房间里的WiFi信号在不断反射** ，当人移动时，这些信号会发生变化。系统通过分析这些变化来判断人体姿态。

**怎么用？**

大致流程比较简单：

  1. 准备支持WiFi信号采集的设备
  2. 安装RuView环境
  3. 采集WiFi信道数据
  4. 模型分析并生成动作结果

项目还提供了一些示例模块，可以直接运行测试。

  

  

项目给出的应用场景比较多，例如：

检测房间里是否有人，识别人类姿态或动作，监测呼吸和心率，灾害救援中寻找被困人员，智能安防和行为监测。

系统可以通过WiFi信号**推算人体姿态和生命体征** ，并且在完全没有摄像头的情况下工作。

这类技术目前还在持续研究阶段，但作为开源项目已经很有探索价值。

  

## 三、QtScrcpy——开源投屏神器！安卓手机实时投屏到电脑，不是模拟器！

项目地址：https://github.com/barry-ran/QtScrcpy

QtScrcpy是一个**安卓实时投屏工具** 。它可以把手机画面直接显示到电脑上，同时还能用键盘和鼠标控制手机。

  

  

和很多投屏软件不同，它**不是模拟器** ，也不需要root权限。

几秒钟之后，手机屏幕就会出现在电脑窗口里。

如果配置无线调试，也可以用WiFi连接。

  

  

开发者调试APP、手游玩家键鼠操作、演示手机功能时，这个工具都比较好用。

# **四.Surge——** 不到 10MB，开源下载神器，速度起飞！

Surge 是一款面向开发者的高级网络调试与代理工具，主要用于网络流量监控、规则转发、HTTPS 解密（MITM）、URL 重写等，支持 iOS、macOS 平台，并可通过配置实现跨设备同步。

GitHub 项目地址：https://github.com/surge-downlo

  

老实说，第一眼就觉得，这玩意有点不一样。它是一个跑在终端里的下载管理器，有一个非常好看的 TUI 界面。但不一样的地方在于，它做了一件事：

把一个文件，拆开，同时开多条连接一起下。简单说就是，浏览器下载是一辆独轮车，一趟一趟往回运。Surge 是直接调来一支车队，把文件切成块，分头跑。最多可以开到 32 条并行连接。

我看了一眼它的 Benchmark，对比数据放在那里。同样下一个 1GB 的文件：wget，61 秒。curl，57 秒。aria2c，40 秒。Surge，**28 秒** 。我当时看了两遍，确认自己没看错。这还不是最爽的。

安装这个事，说实话，让我有点意外，因为真的比我想象的简单多了。

Mac 的话，一行命令：
    
    
    brew install surge-downloader/tap/surge

Windows 的话：
    
    
    winget install surge-downloader.surge

敲完，装好，直接在终端里输入 `surge`，就进了那个好看的 TUI 界面。

没有配置文件，没有注册账号，没有弹窗问你要不要订阅邮件。

就这样，进去了。

Surge 还有一个功能，我觉得对我这种经常同时拉好几个模型权重的人来说，特别实用。

它有一个 Server 模式，可以作为一个后台守护进程跑着。
    
    
    surge server

开起来之后，你在任何一个终端标签里新加下载任务，全都会统一进这一个队列。

开了 10 个标签，也都是同一个下载引擎在调度。

不会出现一堆进程抢带宽互相干扰的情况。

甚至，如果你有个树莓派或者 NAS 放在家里跑着，也可以在上面跑 Surge 的 server mode，然后远程连上去，在本地的 TUI 里统一管理。

本地操作，远端下载，下好了文件已经在 NAS 上了。

有一说一，这个架构设计，对那种经常需要批量拉大模型的人来说，差点没让我觉得有点过分了。

它还有一个浏览器插件，装好之后，你在浏览器里点下载的时候，文件会直接被拦截，扔给 Surge 来处理，而不是走浏览器自己的那个单线程下载器。

Firefox 版本已经在 Mozilla 官方插件商店里了。

Chrome / Edge 的版本目前还在等官方上架，需要手动加载开发者模式来用。

我看了一眼，他们在 README 里写着正在筹钱交 Chrome Web Store 的费用，两个 CS 在读的大学生在课间攒的项目。

两个在考期中间抽时间写代码的学生，把这个工具放出来，免费给所有人用。

他们的 README 里最后写着，如果 Surge 帮你省了时间，可以给他们买杯咖啡。

作为一个爱捣鼓软件的爱好者，我至少用过不下百个免费软件和github上的热门开源项目，但真正对于大多数普通人来说，功能好用、界面简洁是最重要的。

  

## 五、LosslessCut——视频剪辑，真的可以只保留“剪”

  

  

  
GitHub 项目地址：https://github.com/mifi/lossless-cutht  

很多人一听剪辑，就想到PR。

可大部分人真正的需求，只是把视频前后多余的部分剪掉。

在LosslessCut里，你选好起点终点，导出就是成品。

速度快到离谱。因为它做的是“**无损裁剪** ”，几分钟的视频，几秒就能导出。画质不变，文件大小不变。

  

  

界面极简，时间轴清晰。

支持**批量** 处理，适合做**素材整理、监控视频截取、课程片段剪裁** 。

对普通人来说，这种效率远比复杂特效重要。

## 六、Eversheet——不开源但免费！国产表格开发神器，全程零代码！文员也能上手

免费模板一键导入体验：https://iyunbiao.com/appstore/2006.html

很多人每天泡在Excel里。写公式、拉透视表、甚至折腾VBA。

Eversheet中文名叫云表平台。界面是熟悉的表格操作界面，支持Excel批量导入导出，函数逻辑也能兼容。上手门槛很低。

  

  

真正的分水岭在后面。它可以直接在表格基础上做**流程、做权限、做自动化报表** ，甚至开发完整的**企业管理系统** ！

不用写繁琐VBA，不用折腾复杂代码。还可以一键导入做好的**免费软件模板，随时使用** ！

全中文逻辑，自定义业务公式，表单、审批、统计分析都可以零代码、画表格配置。

  

  

国内像中铁十六局、延长石油、许继电气等30万+国内企业，就是基于云表平台搭建自己的**个性化管理系统** ，像ERP、CRM、MES、WMS、进销存等。灵活度高，改需求不用推倒重来。

很多人以为Excel只能做报表或简单软件。当它变成「无代码」系统开发工具，玩法完全不一样。

## 七、n8n——收获17万+收藏，工作流自动化

  

  

开源项目：http://github.com/n8n-io/n8n

**17万+收藏** 。在github里，这个数字已经说明问题。

n8n是一个工作流自动化平台，核心作用是**让不同的软件自动“对话”** ，把琐碎重复的任务自动化。

可本地部署，数据掌握在自己手里。

界面是可视化拖拽，你把触发条件、接口、逻辑节点连起来，一个自动流程就跑起来了。

  

  

**核心用途：**

1.跨平台联动： 比如收到某人的邮件，自动把附件存到网盘，并在微信或钉钉发提醒。

2.信息自动汇总： 定时抓取多个网站的新闻或数据，自动整理到 Excel 表格中。

3.解放双手： 将原本需要人工“复制、粘贴、上传”的流程，变成一键运行的自动流。

## 八、Paper Burner X——打开即用的论文阅读/翻译工具

http://开源项目：  
http://github.com/Feather-2/paper-burner-x

如果你经常查阅国外论文，这个免费开源工具绝对可以派上用场。

Paper Burner X是一个开源的论文阅读工具，目标是让用户更方便地查找和阅读学术论文。

  

  

很多科研网站访问体验并不友好，这个项目尝试做一个更简单的阅读入口。

**主要功能：**

  * PDF在线双语阅读，集合AI能力，**高质量翻译**
  * **增强学术内容展示，** 特别优化了复杂公式的渲染。
  * 浏览器式阅读体验，打开即用

  

  

## 总结

GitHub上真正有意思的项目往往不是那种巨型框架，而是解决具体问题的工具。我发现如果平时只在软件商店找工具，很多好东西很难发现。

所以平日里多逛逛GitHub，经常能淘到一些意想不到的项目。

#   

* * *

  

  

  
  

**END**

  
  
  

**往期精选**

◆[用【Rufus】轻松创建USB启动盘，安装Windows、Linux系统](https://mp.weixin.qq.com/s?__biz=MzUyNTE5MDE3Ng==&mid=2247753955&idx=5&sn=6ff386d659ce060ed094370227075c7f&scene=21#wechat_redirect)

◆[Windows记事本迎史诗级更新：终于能支持图片了](https://mp.weixin.qq.com/s?__biz=MzUyNTE5MDE3Ng==&mid=2247753622&idx=5&sn=7643b2403f2ab8e8a78807213c3d4a8d&scene=21#wechat_redirect)

◆[豆包+即梦 新手全流程详细指南，IA高手绕过](https://mp.weixin.qq.com/s?__biz=MzUyNTE5MDE3Ng==&mid=2247753583&idx=2&sn=e3fcd18032518fa358782557e26bdfca&scene=21#wechat_redirect)

◆[DeepSeek秒转Word秘籍：职场人必备的标准化文档生成指南](https://mp.weixin.qq.com/s?__biz=MzUyNTE5MDE3Ng==&mid=2247753539&idx=5&sn=c8405d2d3de1aa09fbb30adde6a59ccf&scene=21#wechat_redirect)

◆[国产信创操作系统安装（银河麒麟桌面操作系统V10 SP1 HWE X86-2503），附各版本下载链接，收藏](https://mp.weixin.qq.com/s?__biz=MzUyNTE5MDE3Ng==&mid=2247753506&idx=1&sn=a22e926e62d1a478802c08e587f0cea6&scene=21#wechat_redirect)

◆[当前国产综合实力最强的三款AI 工具](https://mp.weixin.qq.com/s?__biz=MzUyNTE5MDE3Ng==&mid=2247753440&idx=5&sn=ca44efac3a4846880cd30457ef3cf58c&scene=21#wechat_redirect)

◆[想让你的照片存储时间更久一些，U盘、光盘、移动硬盘、电脑硬盘、网络云盘、NAS哪种备份方法靠谱？](https://mp.weixin.qq.com/s?__biz=MzUyNTE5MDE3Ng==&mid=2247753211&idx=3&sn=4dc152a95c2ba292f2b5d53114212d7e&scene=21#wechat_redirect)

◆[别再瞎用豆包了！这8个进阶提示词，普通人也能秒变AI高手](https://mp.weixin.qq.com/s?__biz=MzUyNTE5MDE3Ng==&mid=2247753539&idx=6&sn=cb6e4edf424d1108d28385b88080c3b4&scene=21#wechat_redirect)

◆[9款低调黑科技APP，用了再也舍不得删](https://mp.weixin.qq.com/s?__biz=MzUyNTE5MDE3Ng==&mid=2247751756&idx=4&sn=b6ffd636602dcb52fd12118791608894&scene=21#wechat_redirect)

◆[老电脑直接满血复活：老外整的精简Win10太顶了](https://mp.weixin.qq.com/s?__biz=MzUyNTE5MDE3Ng==&mid=2247752294&idx=2&sn=4590683b53d8a5df3c1e4329c2b24002&scene=21#wechat_redirect)

◆[2026年十大NVME固态硬盘排行榜：这10款SSD哪个牌子更抗造](https://mp.weixin.qq.com/s?__biz=MzUyNTE5MDE3Ng==&mid=2247751288&idx=1&sn=90632072f90434257526803945bf805b&scene=21#wechat_redirect)

◆[Win11精简系统Win11 X-Lite 26H1和Tiny11 25H2，谁才是老电脑救](https://mp.weixin.qq.com/s?__biz=MzUyNTE5MDE3Ng==&mid=2247750733&idx=1&sn=0d4c87243afb2fb7e1a8ac77f3efaac5&scene=21#wechat_redirect)星

◆[IP地址就像是互联网上的物理设备的门牌号？看完此文后便明白IP地址的真正含义了](https://mp.weixin.qq.com/s?__biz=MzUyNTE5MDE3Ng==&mid=2247751683&idx=4&sn=c6923623eb35affd03f3d474f603fe10&scene=21#wechat_redirect)

