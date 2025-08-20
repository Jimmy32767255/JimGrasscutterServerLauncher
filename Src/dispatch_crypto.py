def xor_crypt(data: bytes, key: str) -> bytes:
    from loguru import logger
    logger.debug(f"开始XOR加密/解密，数据长度: {len(data)} 字节")
    logger.debug(f"使用的密钥: {key}")
    
    import base64
    try:
        key_bytes = base64.b64decode(key)
    except Exception:
        key_bytes = key.encode('utf-8')
    key_len = len(key_bytes)
    logger.debug(f"密钥字节长度: {key_len}")
    
    result = bytes(data[i] ^ key_bytes[i % key_len] for i in range(len(data)))
    logger.debug(f"XOR操作完成，结果长度: {len(result)} 字节")
    
    return result