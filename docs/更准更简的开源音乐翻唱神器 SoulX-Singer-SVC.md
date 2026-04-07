# 更准更简的开源音乐翻唱神器 SoulX-Singer-SVC

> 来源: https://mp.weixin.qq.com/s/5_0RkKL8B18sM8Sp2GTXzw
> 爬取时间: 2026-04-07T00:06:06.943362


# 更准更简的开源音乐翻唱神器 SoulX-Singer-SVC

在 [高性能高质量控制灵活的开源音乐翻唱神器 SoulX-Singer](https://mp.weixin.qq.com/s?__biz=MzkwOTc3MTY0MQ==&mid=2247485800&idx=1&sn=5c153849679f65291e7febf1aad4938f&scene=21#wechat_redirect) 一文中，我们介绍了 SoulX-Singer 这款开源音乐翻唱神器，但是其操作相对繁琐，比如需要手动调节 metadata.json 和 vocal.mid 文件，最后需要手动操作将生成的人声和伴奏进行融合。且最后的生成的声音感觉差点意思。

本节介绍一款更准更简的开源音乐翻唱模型 SoulX-Singer-SVC（singing voice conversion），该模型是在 SoulX-Singer 的基础上进行微调的一款模型，专门用于音色克隆。

## 效果展示

Prompt 音频

Target 音频

最终音频：

音色比 SoulX-Singer 更像一些。如果感觉合成后的人声比伴奏要高很多，导致伴奏听不到，则可以考虑使用 [高性能高质量控制灵活的开源音乐翻唱神器 SoulX-Singer](https://mp.weixin.qq.com/s?__biz=MzkwOTc3MTY0MQ==&mid=2247485800&idx=1&sn=5c153849679f65291e7febf1aad4938f&scene=21#wechat_redirect) 中介绍的 audacity 软件进行调整。

## 安装

如果想手动安装，使用如下方式即可
    
    
    git clone https://github.com/Soul-AILab/SoulX-Singer.git  
    cd SoulX-Singer  
    conda create -n soulxsinger_env -y python=3.10  
    conda activate soulxsinger_env  
    pip install -r requirements.txt -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host=mirrors.aliyun.com  
    pip uninstall torch torchaudio  
    pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu128  
    hf download Soul-AILab/SoulX-Singer --local-dir pretrained_models/SoulX-Singer  
    hf download Soul-AILab/SoulX-Singer-Preprocess --local-dir pretrained_models/SoulX-Singer-Preprocess  
    python webui_svc.py

## 使用方式

下载一键整合包后，进行解压，双击 `启动svc.bat` 来运行软件。

启动后，总界面如下。

### 使用步骤

**第一步：上传 Prompt 音频和 Target 音频**

Prompt 音频：eg. 自己的声音；Target 音频：eg. “一生有你”原歌曲

**第二步：生成歌声**

先按照下面的“官方使用建议”进行参数调整，之后点击“歌声转换”即可。

### 官方使用建议

  * • 输入：Prompt 音频建议是干净清晰的歌声，Target 音频可以是纯歌声或伴奏，这两者若带伴奏需要勾选分离选项
  * • 变调：Prompt 音频的音域和 Target 音频的音域差距较大的时候，可以尝试开启自动变调或手动调整变调半音数，指定非0的变调半音数时，自动变调不生效，自动混音的伴奏会配合歌声进行升降调（保持同一个八度）；如果 Prompt 音频是女声，将该值调高，该值越高，调越高
  * • 模型参数：一般采样步数越大，生成质量越好，但生成时间也越长；一般cfg系数越大，音色相似度和旋律保真度越高，但是会造成更多的失真，建议取1～3之间的值
  * • 长音频或完整歌曲中，音域变化较大的情况有可能出现音色不稳定，可以尝试分段转换
