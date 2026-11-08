import csv
import os
import json
import time
import random
import requests
def get_json(v,page):
  url = 'https://m.ctrip.com/restapi/soa2/18109/json/getAttractionList'
  payload = {
      "head": {"cid": "09031101119772239373", "ctok": "", "cver": "1.0", "lang": "01",
                "sid": "8888", "syscode": "999", "auth": "", "xsid": ""},
      "scene": "online",
      "districtId": v,
      "index": page,
      "sortType": 1,
      "count": 10,
      "filter": {"filterItems": []},
      "returnModuleType": "product",
  }
  data = json.dumps(payload).encode('utf-8', 'surrogateescape')
  response = requests.post(url, data=data).json()
  return response

def get_data_info(response):
    feeds=response.get('attractionList',[])#attractionlist是页面数据包
    csv_file="data.csv"
    file_exist=os.path.exists(csv_file)
    headers=['景点ID','所在区域','景点名称','评论数量','评分','是否广告','是否推荐','城市名称'
             ,'图片链接','距离市中心距离','标签列表','详情页链接','市场票价','优惠价格'
             , '优惠描述','实际票价','价格类型','价格类型描述','是否免费','经度','维度','热度评分'
             ]
    with open(csv_file, 'a', newline='', encoding='utf-8') as csvfile:
      csvwriter = csv.writer(csvfile)
      if not file_exist:
        csvwriter.writerow(headers)
      rows=[]
      for feed in feeds:
        card=feed.get('card',{})
        coordinate=card.get('coordinate','')
        poiId = card.get('poiId', '')  # 唯一表示
        # 部分卡片类型（景区等）不返回 zoneName，真实名称在 poiName，做交叉兜底，避免名称为空写入 nan
        zone_name = card.get('zoneName', '') or card.get('poiName', '')
        poi_name = card.get('poiName', '') or card.get('zoneName', '')
        title = zone_name  # 景点名称
        region = poi_name  # 所在区域
        commentCount = card.get('commentCount', '')  # 评论数量
        commentScore = card.get('commentScore', '')  # 评分
        isAdvertisement = card.get('isAdvertisement', '')  # 是否为广告内容
        isRecommend = card.get('isRecommend', '')  # 是否被推荐
        districtName = card.get('districtName', '')  # 城市名称
        coverImageUrl = card.get('coverImageUrl', '')  # 图片
        distanceStr = card.get('distanceStr', '')  # 与市中心的具体
        tags_list = card.get('tagNameList', [])  # 标签
        detailUrl = card.get('detailUrl', '')  # 详情页链接
        marketPrice = card.get('marketPrice', '')  # 市场票价
        preferentialPrice = card.get('preferentialPrice', '')  # 优惠价格
        preferentialDesc = card.get('preferentialDesc', '')  # 优惠描述
        price = card.get('price', '免费')  # 实际票价
        priceType = card.get('priceType', '')  # 价格类型
        priceTypeDesc = card.get('priceTypeDesc', '')  # 价格类型描述
        isFree = card.get('isFree', '')  # 是否免费
        longitude = coordinate.get('longitude', '')  # 经度
        latitude = coordinate.get('latitude', '')  # 纬度
        heatScore = card.get('heatScore', '')  # 热度评分
        rows.append([poiId,title,region,commentCount,commentScore,isAdvertisement,isRecommend,districtName
             ,coverImageUrl,distanceStr,tags_list,detailUrl,marketPrice,preferentialPrice
             ,preferentialDesc,price,priceType,priceTypeDesc,isFree,longitude,latitude,heatScore])
        print(rows)
      csvwriter.writerows(rows)


if __name__ == '__main__':
    city_data={
        '北京':1,
        '广州': 152,
        '四川': 100009,
        '西藏': 100003,
        '大连': 4,
        '福州': 104,
        '云南': 100007,


    }
    for k,v in city_data.items():
        for page in range(1,5):
            response=get_json(v,page)
            get_data_info(response)
            time.sleep(random.randint(1,3))

