import json 
from datetime import timedelta,date

code_dict={}
event_dict={}
with open("func/class_schedule/classweek.json", 'r', encoding='utf-8') as f:
    code_dict = json.load(f)

with open("func/class_schedule/sc_event.json", 'r', encoding='utf-8') as f:
    event_dict = json.load(f)


def event_check(date:date):
    e=event_dict.get(date.strftime("%Y/%m/%d"))
    if e:
        return e
    return None


day_map = {'m': '月', 't': '火', 'w': '水', 'h': '木', 'f': '金'}
day_list=["月",'火','水','木','金',"土","日"]

def class_code(date:date):
    return code_dict.get(date.strftime("%Y/%m/%d"))

def class_check_message(date:date):
    code=class_code(date)
    if code is None:
        e=event_check(date)
        if e:
            return "非授業日です。\n"+e+"です。"
        else:
            return "非授業日です。"
    if code[0]=="e":
        exam_map={"1":"前期中間","2":"前期定期","3":"後期中間","4":"後期期末"}
        return exam_map[code[1]]+"試験です。"
    else:
        return day_map[code[0]]+"曜第"+code[1:]+"回授業日です。"


def week_sc(st_date:date):
    fn_date=st_date+ timedelta(days=6)
    d = st_date
    res=[]
    while d <= fn_date:
        content=""
        e=event_check(d)
        if e:
            content+=e
        code=class_code(d)
        w=d.weekday()
        if w<5 and (code is None) and content=="":
            content+="休業日"
        elif not code:
            pass
        elif day_map[code[0]] != day_list[w]:
            if content!="":
                content+=","
            content+=day_map[code[0]]+"曜授業"
        elif code[0] =="e":
            if content!="":
                content+=","
            content+="テスト期間"
        res.append(content)
        d += timedelta(days=1)
    return res

def week_sc_message(st_date:date):
    sc=week_sc(st_date)
    res=""
    for i,youbi in enumerate(sc):
        if youbi=="":
            continue
        res+=day_list[i]+":"+youbi+"\n"
    res+="\n以上"
    return res

if __name__ == "__main__":
    #print(class_check(date.strptime("2026/4/29", "%Y/%m/%d")))
    today = date(2026, 10,8)
    print(week_sc_message(today - timedelta(days=today.weekday())+ timedelta(days=7)))