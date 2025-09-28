import time


def countdown(seconds, title):
    print(f"\n------{title}------")
    while seconds > 0:
        print(seconds)
        time.sleep(1)
        seconds -= 1
    print(f'倒计时结束！！！')


def main():
    start_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    print(f'现在时间是：{start_time},开始工作！！！')
    countdown(10, "背单词")
    break_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
    print(f'现在时间是：{break_time},休息五分钟！！')
    countdown(5, "背单词")
    main()


if __name__ == '__main__':
    while True:
        ready = input("准备？（yes/no）:")
        if ready == 'yes':
            main()
        elif ready == 'no':
            print('继续努力！')
        else:
            print('请重新输入')
            continue
