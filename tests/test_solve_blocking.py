
task_no = 12
print(f"当前大任务号是：{task_no}")

print(f"开始的任务号是：{task_no}")
no = task_no-1
do_locs = ['1.2.3', '1.2.4', '1.2.5', '1.2.6']
for do_loc in do_locs:
    no+=1
    print(f"No: {no}, 任务: {do_loc}")

print(f"最后的任务号是：{no}")


print(f"下一个大任务号是：{task_no+1}")

print("=========================")
this_task_no = 13
print(f"当前任务号是：{this_task_no}")
plc_get_last_task_no = 12
print(f"上一次获取的任务号是：{plc_get_last_task_no}")
if plc_get_last_task_no == this_task_no:
    print("任务号一致")
    this_task_no += 1
    print(f"调整任务号: {this_task_no}")
else:
    print("任务号不一致")
    print(f"无需调整任务号: {this_task_no}")