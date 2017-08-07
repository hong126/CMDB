import json
import hashlib
import time
from django.shortcuts import render, HttpResponse
from server005 import models
from django.conf import settings


# redis/Memcache
# api_key_record = {
#     # "1b96b89695f52ec9de8292a5a7945e38|1501472467.4977243":1501472477.4977243
# }

def asset(request):
    if request.method == 'POST':
        ##新资产信息
        server_info = json.loads(request.body.decode('utf-8'))
        ##服务器的所有资产信息
        hostname = server_info['basic']['data']['hostname']
        ###拿到服务器的名称
        server_obj = models.Server.objects.filter(hostname=hostname).first()  ##拿到hostname（服务器所有数据）这一列数据
        ##拿到server对象，进而可以反向关联，拿到disk，nic等信息
        if not server_obj:  # 判断数据库中有没有这个资产
            return HttpResponse('当前主机名在资产列表中不存在')
        asset_obj = server_obj.asset  ###拿到服务器对应的资产的对象

        # 资产表中以前的资产信息
        ##server_obj 可以找到服务基本信息（单条）
        ##disk_list = server_obj.disk.all()

        for k, v in server_info.items():
            print(k, v)

        #####处理硬盘信息####
        if not server_info['disk']['status']:
            models.ErrorLog.objects.create(content=server_info['disk']['data'], asset_obj=server_obj.asset,
                                            title='【%s】硬盘采集错误信息' % hostname)
            ##出错的话写日志
        new_disk_dict = server_info['disk']['data']
        old_disk_list = models.Disk.objects.filter(server_obj=server_obj)  # queryset对象

        new_slot_list = list(new_disk_dict.keys())
        ###拿到新硬盘的插槽，对应的是拿到硬盘数据的key
        old_slot_list = []  ##拿到老的硬盘槽位信息
        for item in old_disk_list:
            old_slot_list.append(item.slot)

        # 交集：更新[5,]
        update_list = set(new_slot_list).intersection(old_slot_list)
        # 差集: 创建[3]
        create_list = set(new_slot_list).difference(old_slot_list)

        # 差集: 创建[4]
        del_list = set(old_slot_list).difference(new_slot_list)

        if del_list:
            # 删除
            models.Disk.objects.filter(server_obj=server_obj, slot__in=del_list).delete()
            # 记录日志
            models.AssetRecord.objects.create(asset_obj=server_obj.asset, content="移除硬盘：%s" % ("、".join(del_list),))

            # 增加、
        record_list = []
        for slot in create_list:
            disk_dict = new_disk_dict[slot]
            # {'capacity': '476.939', 'slot': '4', 'model': 'S1AXNSAF303909M     Samsung SSD 840 PRO Series
            disk_dict['server_obj'] = server_obj

            models.Disk.objects.create(**disk_dict)
            ##
            temp = "新增硬盘:位置{slot},容量{capacity},型号:{model},类型:{pd_type}".format(**disk_dict)
            record_list.append(temp)
            ##利用format格式化字符串，来记录新增硬盘信息
        if record_list:
            content = ";".join(record_list)
            models.AssetRecord.objects.create(asset_obj=server_obj.asset, content=content)

        # ############ 更新 ############
        record_list = []
        row_map = {'capacity': '容量', 'pd_type': '类型', 'model': '型号'}
        for slot in update_list:
            new_dist_row = new_disk_dict[slot]
            old_disk_row = models.Disk.objects.filter(slot=slot, server_obj=server_obj).first()
            for k, v in new_dist_row.items():
                # k: capacity;slot;pd_type;model
                # v: '476.939''xxies              DXM05B0Q''SATA'
                value = getattr(old_disk_row, k)
                if v != value:
                    record_list.append("槽位%s,%s由%s变更为%s" % (slot, row_map[k], value, v,))
                    setattr(old_disk_row, k, v)
            old_disk_row.save()
        if record_list:
            content = ";".join(record_list)
            models.AssetRecord.objects.create(asset_obj=server_obj.asset, content=content)

###########################内存########

        if not server_info['memory']['status']:  ##判断内存状态是否正确，如果错误日志直接写到Errorlog中
            models.ErrorLog.objects.create(content=server_info['memory']['data'], asset_obj=server_obj.asset,
                                           title='【%s】内存采集错误信息' % hostname)

        new_memory_dict = server_info['memory']['data']
        old_memory_dist = models.Memory.objects.filter(server_obj=server_obj)

        new_slot_list = list(new_memory_dict.keys())  # 获取新的内存槽位信息

        old_slot_list = []
        for item in old_memory_dist:
            old_slot_list.append(item.slot)

        # 根据集合判断新的槽位信息和老的槽位信息，判断是否要更新，增加，删除资产
        # 交集
        update_list = set(new_slot_list).intersection(old_slot_list)
        # 差集:
        create_list = set(new_slot_list).difference(old_slot_list)
        # 差集: 创建[4]

        del_list = set(old_slot_list).difference(new_slot_list)

        if del_list:
            # 删除
            models.Memory.objects.filter(server_obj=server_obj, slot__in=del_list).delete()
            # 记录日志
            models.AssetRecord.objects.create(asset_obj=server_obj.asset, content="移除内存：%s" % ("、".join(del_list),))

            # 增加、
        record_list = []
        for slot in create_list:
            memory_dict = new_memory_dict[slot]
            # {'capacity': '476.939', 'slot': '4', 'model': 'S1AXNSAF303909M     Samsung SSD 840 PRO Series
            memory_dict['server_obj'] = server_obj

            models.Memory.objects.create(**memory_dict)
            ##
            temp = "新增内存:位置{slot},制造商{manufacturer}，容量{capacity},型号:{model},速度:{speed}".format(**memory_dict)
            record_list.append(temp)
            ##利用format格式化字符串，来记录新增内存信息
        if record_list:
            content = ";".join(record_list)
            models.AssetRecord.objects.create(asset_obj=server_obj.asset, content=content)
        ############ 更新 ############
        record_list = []
        row_map = {'capacity': '容量', 'speed': '速度', 'model': '型号'}
        for slot in update_list:
            new_memory_row = new_memory_dict[slot]
            old_memory_row = models.Memory.objects.filter(slot=slot, server_obj=server_obj).first()
            for k, v in new_memory_row.items():
                # k: capacity;slot;pd_type;model
                # v: '476.939''xxies              DXM05B0Q''SATA'
                value = getattr(old_memory_row, k)
                if v != value:
                    record_list.append("槽位%s,%s由%s变更为%s" % (slot, row_map[k], value, v,))
                    setattr(old_memory_row, k, v)
            old_memory_row.save()
        if record_list:
            content = ";".join(record_list)
            models.AssetRecord.objects.create(asset_obj=server_obj.asset, content=content)

    ###########################Server信息#########

        if not server_info['basic']['status']:  ##判断Server状态是否正确，如果错误日志直接写到Errorlog中
            models.ErrorLog.objects.create(content=server_info['cpu']['data'], asset_obj=server_obj.asset,
                                           title='【%s】服务器采集错误信息' % hostname)
        new_cpu_dict = server_info['cpu']['data']
        new_os_dict = server_info['basic']['data']
        old_server_dist = models.Server.objects.filter(server_obj=server_obj)
        print(old_server_dist)

        old_cpu_dist =[]
        for item in old_server_dist:
            old_cpu_dist.append(item.cpu_model)


from django.http import JsonResponse
def servers(request):
    if request.method == 'GET':
        v =models.Server.objects.values('id','hostname')
        servers_list = list(v)
        return JsonResponse(list(v),safe=False)












    return HttpResponse('.........')
