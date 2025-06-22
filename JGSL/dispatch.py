from loguru import logger
import asyncio
import websockets
import json
import base64
import os
from typing import Optional, Dict, List, Callable, Any
from enum import IntEnum
from aiohttp import web
import uuid

class PacketIds(IntEnum):
    """消息包ID枚举"""
    LoginNotify = 1
    TokenValidateReq = 2
    TokenValidateRsp = 3
    GachaHistoryReq = 4
    GachaHistoryRsp = 5
    GetAccountReq = 6
    GetAccountRsp = 7
    GetPlayerFieldsReq = 8
    GetPlayerFieldsRsp = 9
    GetPlayerByAccountReq = 10
    GetPlayerByAccountRsp = 11
    ServerMessageNotify = 12

class DispatchServer:
    """内置调度服务器实现
    
    负责处理WebSocket连接和消息分发
    """
    def __init__(self, host: str = '0.0.0.0', port: int = 443, dispatch_key: str = "", encryption_key: str = ""):
        self.host = host
        self.port = port
        self.dispatch_key = dispatch_key
        self.encryption_key = encryption_key.encode()
        self.clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.server: Optional[websockets.WebSocketServer] = None
        self.handlers: Dict[int, Callable] = {}
        self.callbacks: Dict[int, List[Callable]] = {}
        
        # 注册默认处理器
        self.register_handler(PacketIds.LoginNotify, self.handle_login)
        self.register_handler(PacketIds.TokenValidateReq, self.validate_token)
        self.register_handler(PacketIds.ServerMessageNotify, self.handle_server_message)
        self.register_handler(PacketIds.GachaHistoryReq, self.fetch_gacha_history)
        self.register_handler(PacketIds.GetAccountReq, self.fetch_account)
        self.register_handler(PacketIds.GetPlayerFieldsReq, self.fetch_player_fields)
        self.register_handler(PacketIds.GetPlayerByAccountReq, self.fetch_player_by_account)

    async def handle_connection(self, websocket, path):
        """处理新客户端连接
        
        Args:
            websocket: 客户端WebSocket连接
            path: 连接路径
        """
        client_id = path.lstrip('/')
        self.clients[client_id] = websocket
        logger.info(f"新客户端连接: {client_id} ")

        try:
            async for message in websocket:
                await self.handle_message(client_id, message)
        except websockets.exceptions.ConnectionClosed:
            logger.warning(f"客户端 {client_id} 断开连接")
        finally:
            self.clients.pop(client_id, None)

    async def handle_message(self, client_id: str, message: bytes):
        """处理客户端消息
        
        Args:
            client_id: 客户端ID
            message: 接收到的加密消息
        """
        try:
            # 解密消息
            decrypted = self._xor_decrypt(message)
            data = json.loads(decrypted.decode())
            
            packet_id = data.get("packetId")
            if packet_id in self.handlers:
                await self.handlers[packet_id](client_id, data.get("message"))
            
            # 触发回调
            if packet_id in self.callbacks:
                for callback in self.callbacks[packet_id]:
                    callback(data.get("message"))
            
            logger.debug(f"收到来自 {client_id} 的消息: {data}")
        except Exception as e:
            logger.error(f"处理消息时出错: {e}")

    async def start(self):
        """启动调度服务器"""
        self.server = await websockets.serve(
            self.handle_connection,
            self.host,
            self.port,
            ssl=None  # 可以添加SSL配置
        )
        logger.success(f"调度服务器已启动在 {self.host}:{self.port}")
        
    def register_handler(self, packet_id: PacketIds, handler: Callable):
        """注册消息处理器"""
        self.handlers[packet_id] = handler
        
    def register_callback(self, packet_id: PacketIds, callback: Callable):
        """注册消息回调"""
        if packet_id not in self.callbacks:
            self.callbacks[packet_id] = []
        self.callbacks[packet_id].append(callback)
        
    async def handle_login(self, client_id: str, message: dict):
        """处理登录通知"""
        logger.info(f"客户端 {client_id} 登录: {message}")
        
    async def validate_token(self, client_id: str, message: dict):
        """验证令牌"""
        logger.info(f"客户端 {client_id} 验证令牌: {message}")
        
    async def handle_server_message(self, client_id: str, message: dict):
        """处理服务器消息通知"""
        logger.info(f"服务器消息通知: {message}")
    
    async def fetch_gacha_history(self, client_id: str, message: dict):
        """处理抽卡历史请求
        
        Args:
            client_id: 客户端ID
            message: 请求消息，包含accountId、page和gachaType
        """
        account_id = message.get("accountId")
        page = message.get("page", 1)
        gacha_type = message.get("gachaType", 0)
        
        # 创建响应对象
        response = {"retcode": 0, "records": []}
        
        
        # 发送响应
        await self.send_message(client_id, PacketIds.GachaHistoryRsp, response)
        logger.info(f"已发送抽卡历史响应给客户端 {client_id}")
    
    async def fetch_account(self, client_id: str, message: dict):
        """处理获取账号请求
        
        Args:
            client_id: 客户端ID
            message: 请求消息，包含accountId
        """
        account_id = message.get("accountId")
        
        account = {"id": account_id, "username": f"user_{account_id}", "token": ""}
        
        # 发送响应
        await self.send_message(client_id, PacketIds.GetAccountRsp, account)
        logger.info(f"已发送账号信息响应给客户端 {client_id}")
    
    async def fetch_player_fields(self, client_id: str, message: dict):
        """处理获取玩家字段请求
        
        Args:
            client_id: 客户端ID
            message: 请求消息，包含playerId和fields
        """
        player_id = message.get("playerId")
        fields = message.get("fields", [])
        
        player_data = {"playerId": player_id}
        for field in fields:
            player_data[field] = f"value_of_{field}"
        
        # 发送响应
        await self.send_message(client_id, PacketIds.GetPlayerFieldsRsp, player_data)
        logger.info(f"已发送玩家字段响应给客户端 {client_id}")
    
    async def fetch_player_by_account(self, client_id: str, message: dict):
        """处理通过账号获取玩家请求
        
        Args:
            client_id: 客户端ID
            message: 请求消息，包含accountId和fields
        """
        account_id = message.get("accountId")
        fields = message.get("fields", [])
        
        player_data = {"accountId": account_id, "playerId": 10001}
        for field in fields:
            player_data[field] = f"value_of_{field}"
        
        # 发送响应
        await self.send_message(client_id, PacketIds.GetPlayerByAccountRsp, player_data)
        logger.info(f"已发送通过账号获取玩家响应给客户端 {client_id}")
    
    def _xor_encrypt(self, data: bytes) -> bytes:
        """简单的XOR加密"""
        if not self.encryption_key:
            return data
        return bytes([b ^ self.encryption_key[i % len(self.encryption_key)] 
                     for i, b in enumerate(data)])
        
    def _xor_decrypt(self, data: bytes) -> bytes:
        """简单的XOR解密"""
        return bytes([b ^ self.encryption_key[i % len(self.encryption_key)] 
                     for i, b in enumerate(data)])
    
    def encode_message(self, packet_id: int, message):
        """编码消息
        
        Args:
            packet_id: 消息包ID
            message: 消息内容
            
        Returns:
            编码后的消息对象
        """
        server_message = {
            "packetId": packet_id,
            "message": json.dumps(message) if isinstance(message, (dict, list)) else message
        }
        return server_message
    
    async def send_message(self, client_id: str, packet_id: int, message):
        """发送消息到客户端
        
        Args:
            client_id: 客户端ID
            packet_id: 消息包ID
            message: 消息内容
        """
        if client_id in self.clients:
            # 编码消息
            encoded = self.encode_message(packet_id, message)
            # 序列化为JSON
            serialized = json.dumps(encoded).encode()
            # 加密消息
            encrypted = self._xor_encrypt(serialized)
            # 发送消息
            await self.clients[client_id].send(encrypted)
            logger.debug(f"已发送消息到客户端 {client_id}: {packet_id} - {message}")

    async def stop(self):
        """停止调度服务器"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            logger.info("调度服务器已停止")


class HttpServer:
    """HTTP服务器实现
    
    负责处理HTTP请求，包括认证和地区查询等
    """
    def __init__(self, host: str = '0.0.0.0', port: int = 80, dispatch_seed: bytes = None, dispatch_key: bytes = None):
        self.host = host
        self.port = port
        self.app = web.Application()
        self.runner = None
        self.site = None
        self.dispatch_seed = dispatch_seed or os.urandom(4096)
        self.dispatch_key = dispatch_key or os.urandom(4096)
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
        
        # 创建中国地区列表响应
        region_list_cn = {
            "regionList": servers,
            "clientSecretKey": base64.b64encode(self.dispatch_seed).decode(),
            "clientCustomConfigEncrypted": base64.b64encode(encoded_config).decode(),
            "enableLoginPc": True
        }
        
        # 设置中国地区列表响应
        self.region_list_response_cn = base64.b64encode(json.dumps(region_list_cn).encode()).decode()


class DispatchClient:
    """内置调度客户端实现
    
    负责连接到调度服务器并发送/接收消息
    """
    def __init__(self, server_url: str, client_id: str, encryption_key: str = ""):
        self.server_url = server_url
        self.client_id = client_id
        self.encryption_key = encryption_key.encode() if encryption_key else b""
        self.connection: Optional[websockets.WebSocketClientProtocol] = None
        self.handlers: Dict[int, Callable] = {}
        self.callbacks: Dict[int, List[Callable]] = {}

    async def connect(self):
        """连接到调度服务器"""
        self.connection = await websockets.connect(
            f"{self.server_url}/{self.client_id}",
            ssl=None  # 可以添加SSL配置
        )
        logger.success(f"已连接到调度服务器 {self.server_url} ")
        
        # 连接后发送登录通知
        if self.connection:
            await self.send_message(PacketIds.LoginNotify, self.client_id)

    async def send_message(self, packet_id: int, message):
        """发送消息到调度服务器
        
        Args:
            packet_id: 消息包ID
            message: 要发送的消息内容
        """
        if self.connection:
            # 编码消息
            encoded = self.encode_message(packet_id, message)
            # 序列化为JSON
            serialized = json.dumps(encoded).encode()
            # 加密消息
            encrypted = self._xor_encrypt(serialized)
            # 发送消息
            await self.connection.send(encrypted)
            logger.debug(f"已发送消息: {packet_id} - {message} ")
    
    def encode_message(self, packet_id: int, message):
        """编码消息
        
        Args:
            packet_id: 消息包ID
            message: 消息内容
            
        Returns:
            编码后的消息对象
        """
        server_message = {
            "packetId": packet_id,
            "message": json.dumps(message) if isinstance(message, (dict, list)) else message
        }
        return server_message
    
    def decode_message(self, message: bytes):
        """解码消息
        
        Args:
            message: 加密的消息数据
            
        Returns:
            解码后的消息对象
        """
        # 解密消息
        decrypted = self._xor_decrypt(message)
        # 反序列化消息
        return json.loads(decrypted.decode())
    
    def _xor_encrypt(self, data: bytes) -> bytes:
        """简单的XOR加密"""
        if not self.encryption_key:
            return data
        return bytes([b ^ self.encryption_key[i % len(self.encryption_key)] 
                     for i, b in enumerate(data)])
    
    def _xor_decrypt(self, data: bytes) -> bytes:
        """简单的XOR解密"""
        return self._xor_encrypt(data)  # XOR加密和解密操作相同
    
    def register_handler(self, packet_id: PacketIds, handler: Callable):
        """注册消息处理器"""
        self.handlers[packet_id] = handler
        
    def register_callback(self, packet_id: PacketIds, callback: Callable):
        """注册消息回调"""
        if packet_id not in self.callbacks:
            self.callbacks[packet_id] = []
        self.callbacks[packet_id].append(callback)
    
    async def handle_message(self, message: bytes):
        """处理服务器消息
        
        Args:
            message: 接收到的加密消息
        """
        try:
            # 解码消息
            data = self.decode_message(message)
            
            packet_id = data.get("packetId")
            if packet_id in self.handlers:
                await self.handlers[packet_id](data.get("message"))
            
            # 触发回调
            if packet_id in self.callbacks:
                for callback in self.callbacks[packet_id]:
                    callback(data.get("message"))
            
            logger.debug(f"收到服务器消息: {data}")
        except Exception as e:
            logger.error(f"处理消息时出错: {e}")

    async def close(self):
        """关闭连接"""
        if self.connection:
            await self.connection.close()
            logger.info("已断开与调度服务器的连接")


async def main():
    """主函数，演示如何使用调度服务器和HTTP服务器"""
    # 配置日志
    logger.add("logs/dispatch.log", rotation="10 MB", level="INFO")
    
    # 创建调度服务器
    dispatch_key = "grasscutter"
    encryption_key = "grasscutter"
    dispatch_server = DispatchServer(
        host="0.0.0.0", 
        port=8888, 
        dispatch_key=dispatch_key, 
        encryption_key=encryption_key
    )
    
    # 创建HTTP服务器
    http_server = HttpServer(
        host="0.0.0.0", 
        port=80
    )
    
    # 初始化地区数据
    regions = [
        {
            "Name": "os_usa",
            "Title": "America",
            "Ip": "127.0.0.1",
            "Port": 22102
        }
    ]
    http_server.initialize_regions(regions, "http://127.0.0.1:80")
    
    # 启动服务器
    await dispatch_server.start()
    await http_server.start()
    
    try:
        # 保持服务器运行
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        # 停止服务器
        await dispatch_server.stop()
        await http_server.stop()
        logger.info("服务器已停止")


if __name__ == "__main__":
    # 运行主函数
    asyncio.run(main())