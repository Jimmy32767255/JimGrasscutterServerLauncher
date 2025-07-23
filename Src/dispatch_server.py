import json
import asyncio
import websockets
from loguru import logger
from .dispatch_config import ServerConfig, PacketIds
from typing import Optional, Dict, List, Callable

class DispatchServer:
    """内置调度服务器实现
    
    负责处理WebSocket连接和消息分发
    """
    def __init__(self, config: ServerConfig):
        self.config = config
        self.host = config.host
        self.port = config.dispatch_port
        self.dispatch_key = config.dispatch_key
        self.encryption_key = config.encryption_key.encode()
        self.clients: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.server: Optional[websockets.WebSocketServer] = None
        self.handlers: Dict[int, Callable] = {}
        self.callbacks: Dict[int, List[Callable]] = {}
        
        # 注册默认处理器
        self._register_default_handlers()

    def _register_default_handlers(self):
        """注册默认消息处理器"""
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