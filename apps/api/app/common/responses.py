from typing import Any

def success_response(data:Any =None,message:str="success")-> dict:
    return {
        "success": True,
        "message": message,
        "data": data
    }
    
def  error_response(message:str,code:str="ERROR")-> dict:
    return {
        "success": False,
        "message": message,
        "code": code
    }