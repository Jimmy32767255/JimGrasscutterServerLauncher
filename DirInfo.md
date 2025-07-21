# 目录结构介绍

Assets:JGSL的资源文件目录

Config:JGSL的配置文件和全局配置

Database:公共MongoDB数据库(所有Grasscutter实例都共享同一个MongoDB数据库，只是连接身份不同)

Database\Data:MongoDB数据库的数据文件目录(所有Grasscutter实例的数据文件都存储在这里)

DownloadTemp:JGSL的下载缓存目录(JGSL下载文件时会先下载到这个目录，然后再移动到需要的目录)

Java:公共Java环境(Java\版本号\*)

keystore:公共证书文件目录(所有Grasscutter实例共享同一个证书文件，用于Grasscutter的https加密连接功能)

Logs:JGSL的日志文件(Logs\JGSL.log)

Servers:实例存储目录(Server\实例名称\*)

Server\实例名称\resources:Grasscutter实例的资源文件目录

Server\实例名称\data:Grasscutter实例的数据文件目录

Server\实例名称\packets:Grasscutter实例的包文件目录

Server\实例名称\plugins:Grasscutter实例的插件文件目录

Server\实例名称\cache:Grasscutter实例的缓存文件目录

Server\实例名称\logs\latest.log:Grasscutter实例的日志文件

Server\实例名称\JGSL\:Grasscutter实例中的JGSL文件目录(包含实例信息和配置)

Src:JGSL的代码文件

Themes:JGSL的主题文件目录(包含JGSL的主题文件)

Translations:JGSL的翻译文件

Web:公共网页目录(所有Grasscutter实例共享同一个网页目录，用于Grasscutter的网页功能)