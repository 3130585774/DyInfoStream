import _thread
import execjs
import hashlib
import gzip
import json
import re
import time
import requests
import websocket
from pathlib import Path
from google.protobuf import json_format
from dy_pb2 import PushFrame ,Response,MatchAgainstScoreMessage,LikeMessage,MemberMessage,GiftMessage,ChatMessage,SocialMessage,RoomUserSeqMessage,UpdateFanTicketMessage,CommonTextMessage


liveRoomId = None
ttwid = ""
user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0'


def onMessage(ws: websocket.WebSocketApp, message: bytes):
    wssPackage = PushFrame()
    wssPackage.ParseFromString(message)
    logId = wssPackage.logId
    decompressed = gzip.decompress(wssPackage.payload)
    payloadPackage = Response()
    payloadPackage.ParseFromString(decompressed)
    # 发送ack包
    if payloadPackage.needAck:
        sendAck(ws, logId, payloadPackage.internalExt)
    for msg in payloadPackage.messagesList:
        if msg.method == 'WebcastMatchAgainstScoreMessage':
            unPackMatchAgainstScoreMessage(msg.payload)
            continue

        if msg.method == 'WebcastLikeMessage':
            data = unPackWebcastLikeMessage(msg.payload)
            print(json.dumps(parseLikeMessage(data), ensure_ascii=False))
            continue

        if msg.method == 'WebcastMemberMessage':
            data = unPackWebcastMemberMessage(msg.payload)
            print(json.dumps(parseMemberMessage(data), ensure_ascii=False))
            continue
        if msg.method == 'WebcastGiftMessage':
            data = unPackWebcastGiftMessage(msg.payload)
            print(json.dumps(parseGiftMessage(data), ensure_ascii=False))
            continue
        if msg.method == 'WebcastChatMessage':
            data = unPackWebcastChatMessage(msg.payload)
            print(json.dumps(parseChatMessage(data), ensure_ascii=False))

            continue

        if msg.method == 'WebcastSocialMessage':
            unPackWebcastSocialMessage(msg.payload)
            continue

        if msg.method == 'WebcastRoomUserSeqMessage':
            unPackWebcastRoomUserSeqMessage(msg.payload)
            continue

        if msg.method == 'WebcastUpdateFanTicketMessage':
            unPackWebcastUpdateFanTicketMessage(msg.payload)
            continue

        if msg.method == 'WebcastCommonTextMessage':
            unPackWebcastCommonTextMessage(msg.payload)
            continue


def parseLikeMessage(data):
    LikeMessage = {
        "type": "LikeMessage",
        "name": data['user']['nickName'],
        "uid": data['user']['id'],
        "head_img": data['user']['AvatarThumb']['urlListList'][0],
        "count": data['count'],  # （用户一次性点赞多少）
        "total": data['total'],  # （直播间点赞数）
        "content": f"点赞了{data['count']}次"
    }
    return LikeMessage


def parseMemberMessage(data):
    MemberMessage = {
        "type": "MemberMessage",
        "name": data['user']['nickName'],
        "uid": data['user']['id'],
        "head_img": data['user']['AvatarThumb']['urlListList'][0],
        "count": data['memberCount'],  # （直播间人数）
        "content": f"{data['user']['nickName']}进入直播间"
    }
    return MemberMessage


def parseChatMessage(data):
    ChatMessage = {
        "type": "ChatMessage",
        "name": data['user']['nickName'],
        "uid": data['user']['id'],
        "head_img": data['user']['AvatarThumb']['urlListList'][0],
        "content": data['content']
    }
    return ChatMessage


def parseGiftMessage(data):
    GiftMessage = {
        "type": "GiftMessage",
        "name": data['user']['nickName'],
        "uid": data['user']['id'],
        "head_img": data['user']['AvatarThumb']['urlListList'][0],
        "giftId": data['giftId'],
        "giftCount": data['groupCount'],
        "giftName": data['gift']['name'],
        "content": data['gift']['describe']
    }
    return GiftMessage


def unPackWebcastCommonTextMessage(data):
    commonTextMessage = CommonTextMessage()
    commonTextMessage.ParseFromString(data)
    data = json_format.MessageToDict(commonTextMessage, preserving_proto_field_name=True)
    return data


def unPackWebcastUpdateFanTicketMessage(data):
    updateFanTicketMessage = UpdateFanTicketMessage()
    updateFanTicketMessage.ParseFromString(data)
    data = json_format.MessageToDict(updateFanTicketMessage, preserving_proto_field_name=True)
    return data


def unPackWebcastRoomUserSeqMessage(data):
    roomUserSeqMessage = RoomUserSeqMessage()
    roomUserSeqMessage.ParseFromString(data)
    data = json_format.MessageToDict(roomUserSeqMessage, preserving_proto_field_name=True)
    return data


def unPackWebcastSocialMessage(data):
    socialMessage = SocialMessage()
    socialMessage.ParseFromString(data)
    data = json_format.MessageToDict(socialMessage, preserving_proto_field_name=True)
    return data


# 普通消息
def unPackWebcastChatMessage(data):
    chatMessage = ChatMessage()
    chatMessage.ParseFromString(data)
    data = json_format.MessageToDict(chatMessage, preserving_proto_field_name=True)

    return data


# 礼物消息
def unPackWebcastGiftMessage(data):
    giftMessage = GiftMessage()
    giftMessage.ParseFromString(data)
    data = json_format.MessageToDict(giftMessage, preserving_proto_field_name=True)
    return data


# xx成员进入直播间消息
def unPackWebcastMemberMessage(data):
    memberMessage = MemberMessage()
    memberMessage.ParseFromString(data)
    data = json_format.MessageToDict(memberMessage, preserving_proto_field_name=True)
    return data


# 点赞
def unPackWebcastLikeMessage(data):
    likeMessage = LikeMessage()
    likeMessage.ParseFromString(data)
    data = json_format.MessageToDict(likeMessage, preserving_proto_field_name=True)
    return data


# 解析WebcastMatchAgainstScoreMessage消息包体
def unPackMatchAgainstScoreMessage(data):
    matchAgainstScoreMessage = MatchAgainstScoreMessage()
    matchAgainstScoreMessage.ParseFromString(data)
    data = json_format.MessageToDict(matchAgainstScoreMessage, preserving_proto_field_name=True)
    return data


# 发送Ack请求
def sendAck(ws, logId, internalExt):
    obj = PushFrame()
    obj.payloadType = 'ack'
    obj.logId = logId
    obj.payloadType = internalExt
    data = obj.SerializeToString()
    ws.send(data, websocket.ABNF.OPCODE_BINARY)


def onError(ws, error):
    pass


def onClose(ws, a, b):
    pass


def onOpen(ws):
    _thread.start_new_thread(ping, (ws,))


# 发送ping心跳包
def ping(ws):
    while True:
        obj = PushFrame()
        obj.payloadType = 'hb'
        data = obj.SerializeToString()
        ws.send(data, websocket.ABNF.OPCODE_BINARY)

        time.sleep(10)


def getTimeStamp():
    return str(time.time() * 1000)[:-5]


def wssServerStart(roomId):
    global liveRoomId
    liveRoomId = roomId
    websocket.enableTrace(False)

    
    
    x_bogus = get_signature(roomId, "7370188514644084235")

    websocketUrl = f"wss://webcast5-ws-web-lf.douyin.com/webcast/im/push/v2/?app_name=douyin_web&version_code=180800&webcast_sdk_version=1.0.14-beta.0&update_version_code=1.0.14-beta.0&compress=gzip&device_platform=web&cookie_enabled=true&screen_width=1680&screen_height=1050&browser_language=zh-CN&browser_platform=MacIntel&browser_name=Mozilla&browser_version=5.0%20(Macintosh;%20Intel%20Mac%20OS%20X%2010_15_7)%20AppleWebKit/537.36%20(KHTML,%20like%20Gecko)%20Chrome/126.0.0.0%20Safari/537.36&browser_online=true&tz_name=Asia/Shanghai&cursor=t-1721380775156_r-1_d-1_u-1_fh-7393270946033751092&internal_ext=internal_src:dim|wss_push_room_id:{roomId}|wss_push_did:7370188514644084235|first_req_ms:1721380775068|fetch_time:1721380775156|seq:1|wss_info:0-1721380775156-0-0|wrds_v:7393274111113301134&host=https://live.douyin.com&aid=6383&live_id=1&did_rule=3&endpoint=live_pc&support_wrds=1&user_unique_id=7370188514644084235&im_path=/webcast/im/fetch/&identity=audience&need_persist_msg_count=15&insert_task_id=&live_reason=&room_id={roomId}&heartbeatDuration=0&signature={x_bogus}"
    h = {
        'cookie': "ttwid=" + ttwid,
        'user-agent': user_agent,
    }

    # 创建一个长连接'
    ws = websocket.WebSocketApp(
        websocketUrl, on_message=onMessage, on_error=onError, on_close=onClose,
        on_open=onOpen,
        header=h
    )

    ws.run_forever()

def get_signature(room_id: str, user_unique_id: str) -> str:
        js_code = Path("webcast_signature.js").read_text()
        js_code = f"""
        _navigator = {{
            userAgent: "{user_agent}"
        }};
        {js_code}
        """
        ctx = execjs.compile(js_code)
        raw_string = f"live_id=1,aid=6383,version_code=180800,webcast_sdk_version=1.0.14-beta.0,room_id={room_id},sub_room_id=,sub_channel_id=,did_rule=3,user_unique_id={user_unique_id},device_platform=web,device_type=,ac=,identity=audience"
        x_ms_stub = {"X-MS-STUB": hashlib.md5(raw_string.encode("utf-8")).hexdigest()}
        result = ctx.call("get_signature", x_ms_stub)
        return result.get("X-Bogus")
    
def parseLiveRoomUrl(_url):
    h = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
        'User-Agent': user_agent,
        'cookie': '__ac_nonce=0638733a400869171be51',
    }
    res = requests.get(url=_url, headers=h)
    global ttwid, liveRoomId
    data = res.cookies.get_dict()
    ttwid = data['ttwid']
    res = res.text

    cleaned_content = res.replace('\\n', '\n').replace('\\"', '"').replace('\\\\', '\\')

    pattern_roomid = r'"roomId":"(\d+)"'
    match_roomid = re.search(pattern_roomid, cleaned_content)
    liveRoomId = match_roomid.group(1) if match_roomid else None
    print("liveRoomId:")
    print(liveRoomId)

    wssServerStart(liveRoomId)


if __name__ == '__main__':
    liveurl = "https://live.douyin.com/376893080771" 
    parseLiveRoomUrl(liveurl)