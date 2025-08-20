import os
import json
import uuid
import base64
from aiohttp import web
from loguru import logger
from typing import Dict, List, Any
from .dispatch_config import Configuration

class HttpServer:
    """HTTP服务器实现
    
    负责处理HTTP请求，包括认证和地区查询等
    """
    def __init__(self, config: Configuration):
        self.config = config
        self.host = config.DISPATCH_INFO().bindAddress
        self.port = config.DISPATCH_INFO().bindPort
        self.app = web.Application()
        self.runner = None
        self.site = None
        self.dispatch_seed = os.urandom(4096)
        self.dispatch_key = config.DISPATCH_INFO().encryptionKey.encode()
        self.regions = {}
        self.region_list_response = ""
        self.region_list_response_cn = ""
        
        # 设置路由
        self.setup_routes()
    
    def setup_routes(self):
        """设置HTTP路由"""
        # 默认路由
        self.app.router.add_get('/', self.handle_index)
        
        # 认证相关路由
        self.app.router.add_post('/hk4e_global/mdk/shield/api/login', self.handle_login)
        self.app.router.add_post('/hk4e_global/mdk/shield/api/verify', self.handle_token_login)
        self.app.router.add_post('/hk4e_global/combo/granter/login/v2/login', self.handle_session_key_login)
        
        # 地区查询路由
        self.app.router.add_get('/query_region_list', self.handle_query_region_list)
        self.app.router.add_get('/query_cur_region/{region}', self.handle_query_current_region)
        
        # 中国服务器路由
        self.app.router.add_post('/hk4e_cn/mdk/shield/api/login', self.handle_login)
        self.app.router.add_post('/hk4e_cn/mdk/shield/api/verify', self.handle_token_login)
        self.app.router.add_post('/hk4e_cn/combo/granter/login/v2/login', self.handle_session_key_login)
    
    async def start(self):
        """启动HTTP服务器"""
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, self.host, self.port)
        await self.site.start()
        logger.success(f"HTTP服务器已启动在 {self.host}:{self.port}")
    
    async def stop(self):
        """停止HTTP服务器"""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
        logger.info("HTTP服务器已停止")
    
    async def handle_index(self, request):
        """处理首页请求"""
        return web.Response(text="<html><body><h1>JimGrasscutterServerLauncher</h1></body></html>", content_type='text/html')
    
    async def handle_login(self, request):
        """处理登录请求"""
        try:
            body = await request.json()
            response = {
                "retcode": 0,
                "message": "OK",
                "data": {
                    "account": {
                        "uid": str(uuid.uuid4()),
                        "name": body.get("account", ""),
                        "email": "",
                        "mobile": "",
                        "is_email_verify": "0",
                        "realname": "",
                        "identity_card": "",
                        "token": str(uuid.uuid4()),
                        "safe_mobile": "",
                        "facebook_name": "",
                        "twitter_name": "",
                        "game_center_name": "",
                        "google_name": "",
                        "apple_name": "",
                        "sony_name": "",
                        "tap_name": "",
                        "country": "US",
                        "reactivate_ticket": "",
                        "area_code": "**"
                    },
                    "device_grant_required": False,
                    "safe_mobile_required": False,
                    "realperson_required": False,
                    "reactivate_required": False,
                    "realname_operation": "NONE"
                }
            }
            return web.json_response(response)
        except Exception as e:
            logger.error(f"处理登录请求时出错: {e}")
            return web.json_response({"retcode": -1, "message": str(e)})
    
    async def handle_token_login(self, request):
        """处理令牌登录请求"""
        try:
            body = await request.json()
            response = {
                "retcode": 0,
                "message": "OK",
                "data": {
                    "account": {
                        "uid": body.get("uid", ""),
                        "name": f"user_{body.get('uid', '')}",
                        "email": "",
                        "mobile": "",
                        "is_email_verify": "0",
                        "realname": "",
                        "identity_card": "",
                        "token": body.get("token", ""),
                        "safe_mobile": "",
                        "facebook_name": "",
                        "twitter_name": "",
                        "game_center_name": "",
                        "google_name": "",
                        "apple_name": "",
                        "sony_name": "",
                        "tap_name": "",
                        "country": "US",
                        "reactivate_ticket": "",
                        "area_code": "**"
                    }
                }
            }
            return web.json_response(response)
        except Exception as e:
            logger.error(f"处理令牌登录请求时出错: {e}")
            return web.json_response({"retcode": -1, "message": str(e)})
    
    async def handle_session_key_login(self, request):
        """处理会话密钥登录请求"""
        try:
            body = await request.json()
            response = {
                "retcode": 0,
                "message": "OK",
                "data": {
                    "combo_id": "1",
                    "open_id": body.get("uid", ""),
                    "combo_token": str(uuid.uuid4()),
                    "data": "{}",
                    "heartbeat": False,
                    "account_type": "1"
                }
            }
            return web.json_response(response)
        except Exception as e:
            logger.error(f"处理会话密钥登录请求时出错: {e}")
            return web.json_response({"retcode": -1, "message": str(e)})
    
    async def handle_query_region_list(self, request):
        """处理查询地区列表请求"""
        try:
            # 获取查询参数
            version = request.query.get("version", "")
            platform = request.query.get("platform", "")
            
            # 根据版本和平台确定使用的地区列表
            if version and platform:
                version_code = version[:8]
                if version_code in ["CNRELiOS", "CNRELWin", "CNRELAnd"]:
                    # 使用中国地区列表
                    return web.Response(text=self.region_list_response_cn or "CP///////////wE=")
                elif version_code in ["OSRELiOS", "OSRELWin", "OSRELAnd"]:
                    # 使用海外地区列表
                    return web.Response(text=self.region_list_response or "CP///////////wE=")
            
            # 使用默认地区列表
            return web.Response(text=self.region_list_response or "CP///////////wE=")
        except Exception as e:
            logger.error(f"处理查询地区列表请求时出错: {e}")
            return web.Response(text="CP///////////wE=")
    
    async def handle_query_current_region(self, request):
        """处理查询当前地区请求"""
        try:
            # 获取地区名称
            region_name = request.match_info.get("region", "")
            version = request.query.get("version", "")
            
            # 获取地区数据
            region_data = "CAESGE5vdCBGb3VuZCB2ZXJzaW9uIGNvbmZpZw=="
            if region_name in self.regions:
                region_data = self.regions[region_name]
            
            # 返回地区数据
            return web.Response(text=region_data)
        except Exception as e:
            logger.error(f"处理查询当前地区请求时出错: {e}")
            return web.Response(text="CAESGE5vdCBGb3VuZCB2ZXJzaW9uIGNvbmZpZw==")
    
    def initialize_regions(self, regions: List[Dict[str, Any]], dispatch_domain: str):
        """初始化地区数据
        
        Args:
            regions: 地区配置列表，每个地区包含Name、Title、Ip和Port
            dispatch_domain: 调度服务器域名
        """
        # 创建地区列表
        servers = []
        used_names = []
        
        for region in regions:
            if region["Name"] in used_names:
                logger.error(f"地区名称已被使用: {region['Name']}")
                continue
                
            # 创建地区标识符
            region_info = {
                "name": region["Name"],
                "title": region["Title"],
                "type": "DEV_PUBLIC",
                "dispatchUrl": f"{dispatch_domain}/query_cur_region/{region['Name']}"
            }
            used_names.append(region["Name"])
            servers.append(region_info)
            
            # 创建地区信息对象
            region_data = {
                "gateserverIp": region["Ip"],
                "gateserverPort": region["Port"]
            }
            
            # 创建地区查询响应
            query_data = {
                "regionInfo": region_data,
                "clientSecretKey": base64.b64encode(self.dispatch_seed).decode()
            }
            
            # 将地区数据存储到地区字典中
            self.regions[region["Name"]] = base64.b64encode(json.dumps(query_data).encode()).decode()
        
        # 创建配置对象
        custom_config = {
            "sdkenv": "2",
            "checkdevice": "false",
            "loadPatch": "false",
            "showexception": "true",
            "regionConfig": "pm|fk|add",
            "downloadMode": "0",
            "codeSwitch": [3628],
            "coverSwitch": [40]
        }
        
        # 加密配置
        encoded_config = json.dumps(custom_config).encode()
        encoded_config = bytes([b ^ self.dispatch_key[i % len(self.dispatch_key)] for i, b in enumerate(encoded_config)])
        
        # 创建地区列表响应
        region_list = {
            "regionList": servers,
            "clientSecretKey": base64.b64encode(self.dispatch_seed).decode(),
            "clientCustomConfigEncrypted": base64.b64encode(encoded_config).decode(),
            "enableLoginPc": True
        }
        
        # 设置地区列表响应
        self.region_list_response = base64.b64encode(json.dumps(region_list).encode()).decode()
        
        # 为中国服务器创建配置
        custom_config["sdkenv"] = "0"
        encoded_config = json.dumps(custom_config).encode()
        encoded_config = bytes([b ^ self.dispatch_key[i % len(self.dispatch_key)] for i, b in enumerate(encoded_config)])
        
        region_list_cn = {
            "regionList": servers,
            "clientSecretKey": base64.b64encode(self.dispatch_seed).decode(),
            "clientCustomConfigEncrypted": base64.b64encode(encoded_config).decode(),
            "enableLoginPc": True
        }
        self.region_list_response_cn = base64.b64encode(json.dumps(region_list_cn).encode()).decode()