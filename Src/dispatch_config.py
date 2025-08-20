import json
import secrets
from loguru import logger

class DispatchInfo:
    def __init__(self):
        self.dispatchKey = ""
        self.encryptionKey = ""
        self.dispatchUrl = ""
        self.bindAddress = "0.0.0.0"
        self.bindPort = 8080

class DatabaseInfo:
    def __init__(self):
        self.connectionUri = "mongodb://localhost:27017"
        self.collection = "Grasscutter"

class Configuration:
    _DISPATCH_INFO = None
    _DATABASE_INFO = None

    @classmethod
    def DISPATCH_INFO(cls):
        if cls._DISPATCH_INFO is None:
            cls._DISPATCH_INFO = DispatchInfo()
        return cls._DISPATCH_INFO

    @classmethod
    def DATABASE_INFO(cls):
        if cls._DATABASE_INFO is None:
            cls._DATABASE_INFO = DatabaseInfo()
        return cls._DATABASE_INFO

    @staticmethod
    def load_config(config_path="Config/dispatch_config.json"):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)

            http_config = config_data.get("server", {}).get("http", {})
            dispatch_config = config_data.get("server", {}).get("dispatch", {})

            # 从 dispatch 配置中读取 dispatchKey 和 encryptionKey
            if dispatch_config:
                if dispatch_config.get("dispatchKey") is not None:
                    Configuration.DISPATCH_INFO().dispatchKey = dispatch_config.get("dispatchKey")
                if dispatch_config.get("encryptionKey") is not None:
                    Configuration.DISPATCH_INFO().encryptionKey = dispatch_config.get("encryptionKey")
                if dispatch_config.get("dispatchUrl") is not None:
                    Configuration.DISPATCH_INFO().dispatchUrl = dispatch_config.get("dispatchUrl")
            else:
                # 如果没有dispatch配置，则使用默认值或从http配置中获取
                Configuration.DISPATCH_INFO().dispatchKey = "" # 默认值
                Configuration.DISPATCH_INFO().encryptionKey = "" # 默认值
                # 使用http配置中的bindAddress和bindPort构建dispatchUrl
                bind_address = http_config.get("bindAddress", Configuration.DISPATCH_INFO().bindAddress)
                bind_port = http_config.get("bindPort", Configuration.DISPATCH_INFO().bindPort)
                Configuration.DISPATCH_INFO().dispatchUrl = f"ws://{bind_address}:{bind_port}"

            # 从 http 配置中读取 bindAddress 和 bindPort
            if http_config.get("bindAddress") is not None:
                Configuration.DISPATCH_INFO().bindAddress = http_config.get("bindAddress")
            if http_config.get("bindPort") is not None:
                Configuration.DISPATCH_INFO().bindPort = http_config.get("bindPort")

            database_config = config_data.get("databaseInfo", {})
            if database_config.get("connectionUri") is not None:
                Configuration.DATABASE_INFO().connectionUri = database_config.get("connectionUri")
            if database_config.get("collection") is not None:
                Configuration.DATABASE_INFO().collection = database_config.get("collection")

            logger.info("配置文件加载成功")
        except FileNotFoundError:
            logger.error(f"配置文件 '{config_path}' 未找到！请确保文件存在")
        except json.JSONDecodeError:
            logger.error(f"配置文件 '{config_path}' 格式错误！请检查JSON格式")
        except Exception as e:
            logger.error(f"加载配置文件时发生未知错误：{e}")

def generate_random_key(length=43):
    return secrets.token_urlsafe(length)

# 默认创建一个空的config.json文件
def create_default_config_if_not_exists(config_path="Config/dispatch_config.json"):
    try:
        with open(config_path, 'x', encoding='utf-8') as f:
            default_config = {
                "server": {
                    "dispatch": {
                        "dispatchKey": generate_random_key(),
                        "encryptionKey": generate_random_key(),
                        "dispatchUrl": "ws://127.0.0.1:1145"
                    },
                    "http": {
                        "bindAddress": "127.0.0.1",
                        "bindPort": 1145
                    }
                },
                "databaseInfo": {
                    "connectionUri": "mongodb://localhost:27017",
                    "collection": "Grasscutter"
                }
            }
            json.dump(default_config, f, indent=4, ensure_ascii=False)
            logger.info(f"已创建默认配置文件 '{config_path}' 请根据需要修改")
    except FileExistsError:
        logger.info(f"配置文件 '{config_path}' 已存在，跳过创建")
    except Exception as e:
        logger.error(f"创建默认配置文件时发生错误：{e}")