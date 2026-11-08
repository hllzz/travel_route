import pandas as pd

df = pd.read_csv('data.csv')

df = df.drop_duplicates(subset=['景点ID'])#相同id去重

# 部分景点接口不返回 zoneName，导致景点名称为空、页面显示 nan；
# 用所在区域补全名称，两者都为空时才丢弃该行
df['景点名称'] = df['景点名称'].fillna(df['所在区域'])
df = df.dropna(subset=['景点名称'])#删除景点名字为空的地方

df['评分'] = df['评分'].fillna(0)#用0填补评分为空
df['评论数量'] = df['评论数量'].fillna(0)

df['标签列表'] = df['标签列表'].str.replace('[', '', regex=False).str.replace(']', '', regex=False).str.replace('"', '',
                                                                                                                  regex=False)

df.to_csv('clean.csv', index=False)
