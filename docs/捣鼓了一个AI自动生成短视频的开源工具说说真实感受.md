# 捣鼓了一个AI自动生成短视频的开源工具，说说真实感受

> 来源: https://mp.weixin.qq.com/s/XgFzQxVXGgiS3OCPXyt1Vg
> 爬取时间: 2026-04-07T22:15:24.818621


# 其实我一直想搞点短视频副业来着，但每次打开剪映就犯困——找素材、写文案、配音、剪辑，一套下来大半天就没了，而且我剪出来的东西说实话还不如不剪。之前刷到个数据说2024年全球短视频市场已经突破4000亿美元了，年复合增长率20%以上，确实是个风口。但像我这种又懒又没基础的人，真的只能干看着眼馋。

后来在GitHub上闲逛的时候发现一个叫MoneyPrinterTurbo的项目，Star 54.8K，一看简介：输入一个关键词就能自动生成完整短视频。我当时就想，这也太玄乎了吧，试了下发现还真能用，虽然没有宣传的那么神，但确实帮了大忙。开发者叫harry0703，项目一直在更新维护，不是那种扔上去就不管了的。

## 这玩意到底是啥

简单说就是一个开源的AI短视频生成工具。你给它一个主题或者关键词，比如"春日赏花"，它就自动帮你把一整套流程走完：用大模型写文案→去素材网站搜匹配的视频片段→用TTS把文案读出来变成语音→自动切字幕→配个BGM→最后合成一个完整视频。

跟Sora那种凭空生成画面不一样，它是把已有的无版权素材智能拼接，所以对电脑要求不高，我那台破笔记本都能跑。输出支持横屏16:9（适合YouTube、B站）和竖屏9:16（抖音、快手直接能发），视频素材主要来自Pixabay和Pexels，都是无版权的，不用担心被投诉。

它支持的大模型还挺多的：OpenAI、DeepSeek、Moonshot、通义千问、Google Gemini、Ollama、Azure、文心一言、ModelScope这些都能接。项目README里特别推荐国内用户用DeepSeek或者Moonshot，因为国内直接能访问，注册就送额度，基本够用不花钱。

配音方面有400多种声音可以选，中文英文方言都有，还支持Azure的语音合成（需要配置API Key，但声音更自然）。字幕的字体、颜色、大小、位置、描边都能自定义。另外还有个GPT-SoVITS配音的功能在路上，据说能让合成声音更自然、情绪更丰富。

## 部署过程

说实话部署这块对纯小白还是有点门槛的，我前后折腾了差不多一个小时才完全跑通。项目提供了好几种部署方式，下面一个个说。

### 方式一：借助workbuddy安装（最简单，推荐新手）

需要我们提前安装好workbuddy，官方下载链接：https://copilot.tencent.com/work/

这是借助workbuddy的“日常办公”任务，全程只需要我们如下图所示下达安装命令

workbuddy会自动帮我们安装，遇到报错信息也会自己解决，最终结束后也会进行提示。整个过程可能会稍微比较久，需要耐心等待一下，显示以下内容就是安装成功啦。

### 方式二：一键启动包（超简单）

这个是官方提供的打包好的版本，不用装Python不用配环境，下载解压直接用。

  * 百度网盘（v1.2.6）: https://pan.baidu.com/s/1wg0UaIyXpO3SqIpaq790SQ?pwd=sbqx 提取码: sbqx
  * Google Drive (v1.2.6): https://drive.google.com/file/d/1HsbzfT7XunkrCrHw5ncUjFX8XX4zAuUh/view?usp=sharing

> 注意路径里不要有中文、特殊字符或者空格，不然会出各种奇怪的报错。我第一次解压到"下载\MoneyPrinterTurbo 新版"这个路径，死活启动不了，后来改成纯英文路径就好了。

解压完建议先双击执行 `update.bat` 更新到最新代码，然后双击 `start.bat` 启动。启动后会自动打开浏览器，如果打开是空白页面，换Chrome或者Edge试试，有些浏览器兼容性不太好。

但这种方式有个缺点：版本更新不够及时，而且出了问题不太好排查，因为你不知道里面的环境到底是怎么配的。适合纯体验一下，真要长期用还是建议手动部署。

### 方式三：本地手动部署（最灵活，推荐长期用）

这是我最后采用的方式，虽然步骤多一点，但出了问题好排查，也方便后续更新。

**第一步：准备环境**

你需要提前装好这些东西：

  * Python 3.11（注意，必须是3.11，我一开始偷懒用的系统自带的3.12，pip install的时候各种依赖冲突报错，折腾了半天最后老老实实装3.11）
  * Git（这个一般都有）
  * Miniconda或者Anaconda（推荐用conda管理虚拟环境，避免污染系统环境）

**第二步：ImageMagick**

这个是视频合成时处理图片的依赖，不同系统装法不一样：

Windows用户：

到https://imagemagick.org/script/download.php 下载，切记一定要选静态库版本，文件名里带"static"的那个，比如 `ImageMagick-7.1.1-32-Q16-x64-static.exe`。安装的时候不要修改默认安装路径！装完之后要去改config.toml里的 `imagemagick_path` 为你实际的安装路径。我第一次装的时候选了非静态库版本，后面合成视频的时候各种报错，排查了好久。

MacOS用户：
    
    
    brew install imagemagick

Ubuntu用户：
    
    
    sudo apt-get install imagemagick

CentOS用户：
    
    
    sudo yum install ImageMagick

**第三步：克隆项目并安装依赖**
    
    
     git clone https://github.com/harry0703/MoneyPrinterTurbo.git  
    cd MoneyPrinterTurbo  
    conda create -n MoneyPrinterTurbo python=3.11  
    conda activate MoneyPrinterTurbo  
    pip install -r requirements.txt

这一步可能会比较慢，特别是国内网络，pip下载一些包可能会超时。建议换一个国内源，比如清华源或者阿里源，速度能快不少。另外requirements.txt里依赖挺多的，耐心等它装完，中途报错的话大概率是网络问题，重新跑一遍pip install就好。

**第四步：配置config.toml**

项目根目录下有个 `config.example.toml`，复制一份改名为 `config.toml`，然后按里面的注释配置。主要需要填的：

  * `pexels_api_keys`：去pexels.com注册一个账号，拿到API Key填进去。这个是免费的，素材搜索就靠它。
  * `llm_provider`：选你要用的大模型。国内推荐填 `deepseek` 或者 `moonshot`，注册就送额度，不用花钱。
  * 对应的API Key：根据你选的provider，填对应的API Key。

我当时选的DeepSeek，注册完送了大概够用几十个视频的额度，对于体验来说完全够了。一开始我选的OpenAI，结果发现需要科学上网才能调用，又换回DeepSeek了。

还有一个 `subtitle_provider` 配置，默认是 `edge`，生成速度快但偶尔质量不太稳定。如果字幕效果不好的话可以改成 `whisper`，质量更好但需要额外下载一个大约3GB的模型文件（国内访问HuggingFace不方便，项目README里提供了百度网盘和夸克网盘的下载链接，搜"字幕生成"就能找到）。下载后解压放到 `.\MoneyPrinterTurbo\models\whisper-large-v3` 目录下。

**第五步：启动**

在项目根目录下执行：

Windows：
    
    
    webui.bat

Mac/Linux：
    
    
    sh webui.sh

启动后浏览器自动打开 `127.0.0.1:8501`，就是Web界面了。

如果想用API方式调用（比如想批量生成或者接自己的工作流）：
    
    
    python main.py

API文档地址是 `http://127.0.0.1:8080/docs` 或者 `http://127.0.0.1:8080/redoc`，可以直接在线调试。

### 方式四：Docker部署

如果你不想折腾Python环境，Docker也是个选择，不过需要先装好Docker。

Windows用户注意，需要先装WSL2，参考微软的官方文档：

  * https://learn.microsoft.com/zh-cn/windows/wsl/install
  * https://learn.microsoft.com/zh-cn/windows/wsl/tutorials/wsl-containers

Docker Desktop下载地址：https://www.docker.com/products/docker-desktop/

装好Docker之后：
    
    
    cd MoneyPrinterTurbo  
    docker compose up

注意新版Docker安装时会自动以插件形式安装docker compose，启动命令是 `docker compose up`（中间没有横杠），不是老版本的 `docker-compose up`。

启动后：

  * Web界面访问 `http://0.0.0.0:8501`
  * API文档访问 `http://0.0.0.0:8080/docs`

Docker方式的好处是环境完全隔离，不会污染你的系统，但缺点是出了问题不太好调试，而且占用磁盘空间比较大。

### 方式五：Google Colab在线体验

如果你连本地都不想折腾，项目还提供了Google Colab的notebook，直接在浏览器里就能跑，不需要任何本地环境。不过Colab的免费版GPU资源有限，速度可能比较慢，而且每次都要重新装依赖。

链接地址：https://colab.research.google.com/github/harry0703/MoneyPrinterTurbo/blob/main/docs/MoneyPrinterTurbo.ipynb

## 怎么用这个工具

### 界面基本操作

WebUI打开之后界面其实挺直观的

主要分几个区域：

顶部是基础设置：

  * **模型选择** 推荐直接选择DeepSeek
  * **API KEY** 可以在https://api.deepseek.com申请，或使用第三方厂商，我这里使用的是硅基流动的接口
  * **Base Url** 模型调用地址，https://api.deepseek.com/v1
  * **模型名称** DeepSeek-V3.2
  * **视频源设置** 需要我们去https://www.pexels.com/api/注册账号，获取到放在这里。

左边是参数配置区：

  * **视频主题/关键词** 你输入想要做的视频主题，比如"旅行的意义"、"健身入门"之类的
  * **视频文案** 可以留空让它自动生成，也可以自己写一段，支持中文和英文
  * **视频尺寸** 竖屏9:16（抖音快手）或横屏16:9（YouTube B站）
  * **视频片段时长** 每个素材片段的长度，默认3秒，可以调
  * **素材来源** 目前主要支持Pixabay，也支持Pexels
  * **视频拼接模式** random随机或按顺序

中间是语音设置区：

  * **配音声音** 400多种可选，建议先点试听听一下再决定，有的声音很自然有的就比较机械
  * **语音速度** 默认1.0，可以加快或放慢
  * **语音音量默认1.0**

右边是字幕和背景音乐设置：

  * **字幕开关** 可以开启或关闭
  * **字幕位置** 底部、顶部、或者自定义百分比位置
  * **字体** 默认用MicrosoftYaHeiBold，也可以换成自己放进去的字体（字体文件放到 `resource/fonts` 目录下）
  * **字幕大小** 默认60
  * **字幕颜色** 默认白色加黑色描边，可以自定义
  * **背景音乐** 默认random随机选，也可以指定。BGM文件放在 `resource/songs` 目录下，可以自己添加
  * **背景音乐音量** 默认0.2，建议别调太高，不然会盖过配音

### 生成视频的完整流程

我以"请介绍一下朝鲜和韩国的近代史"这个主题为例，说一下完整的生成过程和时间：

  1. 输入主题"请介绍一下朝鲜和韩国的近代史"，其他参数保持默认，点击生成
  2. 大模型开始写文案，大概几秒钟就出来了，生成了一段关于早市和夜市的描述
  3. 系统根据文案自动提取关键词：Korean modern history, Korean War conflict, DMZ border Korea, North Korea isolation, South Korea development
  4. 视频设置模块采用的是默认设置
  5. 音频模块TTS服务器选择的是SiliconFlow TTS，朗读声音默认
  6. TTS生成语音，选的中文男声，大概3-4秒
  7. 字幕设置采用的默认设置
  8. 最后合成视频，把素材剪切、缩放、拼接、叠字幕、加BGM，大概58分钟，视频时长01：15

视频生成好后，会将保存到的文件夹自动打开展示出来。

整个流程从点生成到拿到成片，将近一小时左右。说实话这个速度稍微有点慢，但全程不需要人为干预，也能接受，毕竟手动做同样的内容少说也得两三个小时。不过也有网友表示生成速度很快，几分钟就能搞定，盲猜可能和电脑网络以及电脑性能有关系。

### 关于费用

音频和视频文案我都是采用的 **硅基流动** 付费版本，一条视频产生的费用是0.11元

### 最终效果

### 批量生成

一次可以设置生成多个视频（video_count参数），系统会一次性生成几个版本，最好挑一最好的发。这个功能对于批量做内容的人来说特别实用，因为每次生成的素材匹配和文案都有些差异，多生成几个总能挑到满意的。

## 我踩过的坑和常见问题

这一块我觉得是最有价值的，因为官方文档里有些问题没写清楚，我是自己踩了坑才搞明白的。

### 1\. Python版本不对

必须用3.11。我一开始用3.12，pip install的时候好几个包装不上，报各种版本冲突。后来换成3.11，一切顺利。别问为什么，照做就行。

### 2\. ImageMagick选错版本

Windows用户下载ImageMagick的时候，一定要选带"static"的版本。我第一次下了个普通版本，结果合成视频时报错说找不到ImageMagick的某些库文件。另外安装路径别改，改了的话config.toml里的 `imagemagick_path` 也要跟着改，容易搞混。

### 3\. 路径有中文或空格

不管是项目路径还是视频输出路径，都不要包含中文、特殊字符或者空格。我试过把项目放在"D:\我的工具\MoneyPrinterTurbo"下，各种报错。后来放到纯英文路径就好了。

### 4\. ImageMagick的policy.xml权限问题

在Linux系统上，ImageMagick默认禁止通过文件读写操作，会导致字幕渲染失败。解决方法是找到ImageMagick的policy.xml配置文件（通常在 `/etc/ImageMagick-X/` 目录下），把 `pattern="@"` 那一行的 `rights="none"` 改成 `rights="read|write"`。

### 5\. Whisper模型下载失败

如果用whisper模式生成字幕，第一次会自动从HuggingFace下载一个大约3GB的模型。国内网络基本连不上HuggingFace，会报 `LocalEntryNotFoundError` 或者 `Cannot find an appropriate cached snapshot folder` 这种错误。

解决方法是手动下载模型文件，项目README里提供了百度网盘和夸克网盘的链接。下载后解压放到 `.\MoneyPrinterTurbo\models\whisper-large-v3` 目录下，确保最终的文件路径结构是：
    
    
    MoneyPrinterTurbo  
     ├─models  
     │ └─whisper-large-v3  
     │   config.json  
     │   model.bin  
     │   preprocessor_config.json  
     │   tokenizer.json  
     │   vocabulary.json

### 6\. ffmpeg找不到

通常情况下ffmpeg会被自动下载并检测到，但偶尔会遇到报错：
    
    
    RuntimeError: No ffmpeg exe could be found.  
    Install ffmpeg on your system, or set the IMAGEIO_FFMPEG_EXE environment variable.

解决方法：去 https://www.gyan.dev/ffmpeg/builds/ 下载ffmpeg，解压后在config.toml里设置 `ffmpeg_path` 为实际路径。

### 7\. 系统文件打开数限制

有时候批量生成或者下载大量素材时会报错，提示文件打开数太多。这是Linux系统的限制，用以下命令查看和修改：
    
    
    # 查看当前限制  
    ulimit -n  
      
    # 调高限制  
    ulimit -n 10240

### 8\. 网络问题导致素材下载失败

确保你的网络是正常的，如果需要科学上网的话VPN要开全局模式。素材下载走的是Pixabay和Pexels的API，有些地区可能会被限速或者连接超时。如果经常下载失败，可以试试换一个网络环境，或者在config里配置代理。

### 9\. 浏览器打开空白页

启动后自动打开的浏览器页面如果是空白的，大概率是浏览器兼容性问题。换成Chrome或者Edge就好了。有些国产浏览器内核版本太低，不支持WebUI的某些特性。

### 10\. BGM太少

项目默认就放了几首背景音乐，在 `resource/songs` 目录下。说实话翻来覆去就那几首，听多了确实腻。建议自己准备一些无版权的音乐放进去，B站和YouTube上搜"no copyright music"一大堆。

## 使用成本

这个得说一下，毕竟不是完全免费的：

  * **工具本身** 完全免费开源，这个没得说
  * **素材** Pixabay和Pexels都是免费无版权的，不花钱
  * **大模型API** 这是主要成本。DeepSeek、Moonshot以及 **硅基流动** 送的额度对于日常体验来说够用了，但如果要批量生产内容，可能需要充点钱。不过相比剪映会员之类的，还是便宜很多的
  * **语音合成** 默认的免费声音就够用，Azure的声音更自然但需要Azure的API Key，Azure有免费额度可以申请
  * **字幕** 用edge模式完全免费，whisper模式需要本地算力但也不花钱

总体来说，对于个人用户和小规模使用，基本可以做到零成本。

## 体验总结

用了段时间，说说真实感受。

**优点：**

  * 确实省精力，从输入到成片不需要我们操作，只等待生成完毕就可以
  * 零版权风险，素材全走的无版权库
  * 可定制空间大，字幕、配音、BGM都能调
  * 支持批量生成，批量做内容的时候特别爽
  * 开源免费，大模型选择多，不绑定任何一家
  * API接口齐全，方便二次开发和自动化

**缺点：**

  * 素材库依赖Pixabay和Pexels，冷门主题匹配不太行
  * 默认BGM太少，得自己准备
  * 生成的内容偏素材混剪风格，画面跟文案的契合度时好时坏
  * 字幕偶尔有时间轴偏移，不影响大局但看着不太舒服

**评分：**

  * 上手难度：6/10（有编程基础的话3/10，纯小白可能要8/10）
  * 部署难度：5/10（照着文档来基本能跑通，但踩坑是免不了的）
  * 功能完整度：7.5/10（该有的基本都有，还有进步空间）
  * 生成质量：7/10（热门主题效果不错，冷门的一般）
  * 性价比：9/10（开源免费，大模型费用也很低）
  * 总体推荐度：7.5/10

**给想试的朋友几个建议：**

  1. 第一次用建议选DeepSeek或Moonshot作为大模型，国内直接能访问，注册还送额度
  2. 字幕先用edge模式，够用就别换whisper，省得折腾
  3. 别期望太高，它就是个"快速出片"的工具，不是专业剪辑软件的替代品
  4. 如果你连部署都懒得折腾，可以去reccloud.cn试试，这是基于MoneyPrinterTurbo做的在线版本，不用部署直接用（项目官方推荐的）
  5. 做内容之前先想好主题，尽量选大众化的、素材容易找的主题，生成效果会好很多

项目地址：https://github.com/harry0703/MoneyPrinterTurbo

硅基流动：https://cloud.siliconflow.cn/i/rcYQ4m9j

往期精彩

