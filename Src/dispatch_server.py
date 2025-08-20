import asyncio
import json
from loguru import logger
from websockets.server import serve
from websockets.exceptions import ConnectionClosedOK
import asyncio

from config import Configuration
from crypto import xor_crypt

class PacketIds:
    LOGIN_NOTIFY = 1
    TOKEN_VALIDATE_REQ = 2
    GET_ACCOUNT_REQ = 3
    SERVER_MESSAGE_NOTIFY = 4
    TOKEN_VALIDATE_RSP = 5
    GET_ACCOUNT_RSP = 6

class DispatchServer:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.handlers = {
            PacketIds.LOGIN_NOTIFY: self.handle_login,
            PacketIds.TOKEN_VALIDATE_REQ: self.validate_token,
            PacketIds.GET_ACCOUNT_REQ: self.fetch_account,
            # PacketIds.SERVER_MESSAGE_NOTIFY: ServerMessageEvent.invoke, # 暂时不实现事件
        }
        self.websocket_server = None # 初始化websocket_server为None
        logger.info(f"Dispatch server 将在 {self.host}:{self.port} 启动")

    async def start(self, stop_event: asyncio.Event):
        try:
            # 尝试启动websocket服务器
            self.websocket_server = await serve(self.handle_connection, self.host, self.port)
            logger.info(f"Dispatch server 已在 {self.host}:{self.port} 启动")
            # 添加端口监听状态检查
            logger.info(f"端口 {self.port} 监听状态: {'成功' if self.websocket_server.sockets else '失败'}")
            # 添加心跳检测
            heartbeat_task = asyncio.create_task(self.heartbeat_check())
            await stop_event.wait()  # 等待停止事件
            logger.info("停止事件已触发，正在关闭Dispatch server...")
            heartbeat_task.cancel() # 取消心跳任务
        except asyncio.CancelledError:
            logger.info("Dispatch server 任务被取消，正在关闭...")
            if self.websocket_server:
                logger.info("正在关闭websocket服务器...")
                await self.websocket_server.close()
                logger.info("Dispatch server 已关闭。")
        except Exception as e:
            logger.error(f"Dispatch server 启动或运行失败: {e} ")
            raise
        finally:
            pass # 确保在任何情况下都尝试关闭websocket服务器，但已在CancelledError中处理

    async def heartbeat_check(self):
        while True:
            await asyncio.sleep(5)
            logger.trace(f"Dispatch server 心跳检测: 运行中")

    async def handle_connection(self, websocket):
        logger.debug(f"Dispatch 客户端已连接：{websocket.remote_address} ")
        try:
            logger.debug(f"开始接收来自 {websocket.remote_address} 的消息...")
            async for message in websocket:
                logger.debug(f"收到来自 {websocket.remote_address} 的原始消息，长度：{len(message)} 字节")
                await self.on_message(websocket, message)
        except ConnectionClosedOK:
            logger.debug(f"Dispatch 客户端已正常断开连接：{websocket.remote_address} ")
        except Exception as e:
            logger.error(f"处理客户端 {websocket.remote_address} 连接时发生错误：{e} ")
            logger.error(f"错误详情：{type(e).__name__}, {str(e)}")

    async def on_message(self, websocket, message):
        logger.debug(f"收到来自 {websocket.remote_address} 的原始消息，长度：{len(message)} 字节")
        try:
            # 解密消息
            logger.debug(f"开始使用密钥解密消息...")
            decrypted_message = xor_crypt(message, Configuration.DISPATCH_INFO().encryptionKey)
            logger.debug(f"解密后消息长度：{len(decrypted_message)} 字节")
            
            # 解码为UTF-8字符串
            try:
                decoded_message = decrypted_message.decode('utf-8')
            except UnicodeDecodeError:
                # 如果UTF-8解码失败，尝试使用latin1编码
                decoded_message = decrypted_message.decode('latin1')
            logger.debug(f"解码后消息长度：{len(decoded_message)} 字符")
            logger.debug(f"原始解码内容：{decoded_message[:100]}..." if len(decoded_message) > 100 else f"原始解码内容：{decoded_message}")

            # 尝试解析为JSON对象
            logger.debug(f"尝试解析消息为JSON...")
            try:
                json_message = json.loads(decoded_message)
                logger.debug(f"成功解析为JSON对象，packetId: {json_message.get('packetId')}")
            except json.JSONDecodeError:
                logger.debug(f"首次JSON解析失败，尝试处理为字符串...")
                # 如果是纯字符串，尝试去除引号和转义
                if decoded_message.startswith('"') and decoded_message.endswith('"'):
                    decoded_message = decoded_message[1:-1]
                decoded_message = decoded_message.replace('"', '"').replace('\\', '')
                logger.debug(f"处理后字符串内容：{decoded_message[:100]}..." if len(decoded_message) > 100 else f"处理后字符串内容：{decoded_message}")
                json_message = json.loads(decoded_message)

            packet_id = json_message.get("packetId")
            data = json_message.get("message") # 与Java的encodeMessage对应

            # 如果data是字符串，尝试再次解析为JSON对象
            if isinstance(data, str):
                try:
                    data = json.loads(data)
                except json.JSONDecodeError:
                    logger.error(f"无法解析data字段为JSON：{data} ")
                    return

            # 检查客户端是否已认证，除了登录包
            if packet_id != PacketIds.LOGIN_NOTIFY:
                if not getattr(websocket, 'is_authenticated', False):
                    logger.warning(f"收到来自未认证客户端的数据包ID：{packet_id} ")
                    await websocket.close()
                    return

            if packet_id in self.handlers:
                await self.handlers[packet_id](websocket, data)
            else:
                logger.warning(f"未知的数据包ID：{packet_id} ")
        except json.JSONDecodeError:
            logger.error(f"无法解析JSON消息：{message} ")
        except Exception as e:
            logger.error(f"处理消息时发生错误：{e} ")

    async def send_message(self, websocket, packet_id, data):
        # 编码消息，与Java的encodeMessage对应
        # Java的message字段是toJson(message)，所以这里也需要先dumps一次
        message_obj = {"packetId": packet_id, "message": json.dumps(data, ensure_ascii=False)}
        encoded_message = json.dumps(message_obj, ensure_ascii=False).encode('utf-8')
        # 加密消息
        encrypted_message = xor_crypt(encoded_message, Configuration.DISPATCH_INFO().encryptionKey)
        await websocket.send(encrypted_message)

    async def handle_login(self, websocket, data):
        logger.debug(f"处理登录请求，原始数据：{data}")
        # Java的handleLogin中，data是getAsString().replaceAll("\"", ""), 所以这里也需要处理
        dispatch_key = data.replace('"', '') if isinstance(data, str) else data
        logger.debug(f"处理后Dispatch Key：{dispatch_key}")
        logger.debug(f"配置中的Dispatch Key：{Configuration.DISPATCH_INFO().dispatchKey}")
        
        if dispatch_key == Configuration.DISPATCH_INFO().dispatchKey:
            websocket.is_authenticated = True # 标记为已认证
            logger.info(f"客户端 {websocket.remote_address} 登录成功")
            logger.debug(f"已设置客户端 {websocket.remote_address} 为已认证状态")
        else:
            logger.warning(f"来自 {websocket.remote_address} 的 Dispatch 密钥无效")
            logger.warning(f"提供的Key：{dispatch_key}，期望的Key：{Configuration.DISPATCH_INFO().dispatchKey}")
            await websocket.close()
            logger.debug(f"已关闭未通过认证的客户端 {websocket.remote_address} 的连接")

    async def validate_token(self, websocket, data):
        # 假设data是包含uid和token的字典
        account_id = data.get("uid")
        token = data.get("token")

        from database import DatabaseHelper

        account = DatabaseHelper.get_account_by_id(account_id)
        valid = account is not None and account.get("token") == token
        account_info = None
        if valid:
            account_info = account.copy()
            account_info.pop('_id', None) # 移除MongoDB的_id字段
            # 确保token字段名称正确，如果Java端是getToken()，这里可能需要调整
            # account_info["token"] = account_info.pop("token", None) # 如果需要重命名token字段

        response = {"valid": valid}
        if valid:
            response["account"] = account_info

        await self.send_message(websocket, PacketIds.TOKEN_VALIDATE_RSP, response)

    async def fetch_account(self, websocket, data):
        # 假设data是包含accountId的字典
        account_id = data.get("accountId")

        from database import DatabaseHelper

        account = DatabaseHelper.get_account_by_id(account_id)
        account_info = None
        if account:
            account_info = account.copy()
            account_info.pop('_id', None) # 移除MongoDB的_id字段

        await self.send_message(websocket, PacketIds.GET_ACCOUNT_RSP, account_info)