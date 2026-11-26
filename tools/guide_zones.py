"""Editorial content for the nine Chinese PCB guide illustrations.

Crops are (left, top, right, bottom) in millimetres from the board's top left.
Each flow names its illustrated stages and the pad-to-pad routes to highlight.
A ⇄ on an edge denotes traffic or winding current in either direction.
"""

from dataclasses import dataclass


@dataclass
class Flow:
    title: str
    stages: str
    note: str
    routes: tuple[str, ...] = ()


@dataclass
class Zone:
    id: str
    name: str
    summary: str
    crops: list
    flows: list[Flow]


def motor(x_axis):
    axis, driver, plug, gpio, pins, shunts, addr, belt = (
        ("X", "U5", "J3", "25 / 26", (10, 11), "R17 / R18", 0, "右侧电机 B · 上层皮带")
        if x_axis else
        ("Y", "U6", "J4", "21 / 22", (33, 36), "R19 / R20", 1, "左侧电机 A · 下层皮带")
    )
    window = (7.5, 24.5, 35, 50) if x_axis else (36, 25, 60, 50)
    sense_a, sense_b = shunts.split(" / ")
    return Zone(axis.lower(), f"{axis} 电机驱动", f"{belt}。一个 STEP 脉冲推进一个微步，DIR 决定方向。",
                [(driver + " 与 " + plug, window)], [
        Flow("步进和方向", f"pulse:GPIO{gpio} → io:STEP / DIR → chip:{driver} 微步控制",
             "两根逻辑线独立传递节拍和方向。共享 ENN 为低时，驱动器可给绕组通电。",
             (f"U2.{pins[0]} > {driver}.16", f"U2.{pins[1]} > {driver}.19")),
        Flow("两相绕组电流", f"rail:12 V → bridge:{driver} 双 H 桥 ⇄ coil:{plug} 两相绕组",
             f"{plug} 的 1、2 脚接 A 相，3、4 脚接 B 相。桥臂交替改变极性，每相电流都可反向。",
             tuple(f"{driver}.{p} <> {plug}.{j}" for p, j in ((24, 1), (21, 2), (26, 3), (1, 4)))),
        Flow("电流闭环", f"bridge:桥臂回流 → resistor:{shunts} → chip:{driver} 采样比较",
             "每相电流在 0.100 Ω 分流器上产生压降。芯片检测压降并调节桥臂导通时间。",
             (f"{driver}.23 > {sense_a}.1", f"{driver}.27 > {sense_b}.1")),
        Flow("串口配置", f"chip:ESP32 ⇄ io:TMC_BUS ⇄ chip:{driver} 地址 {addr}",
             "共享单线 UART 为 115200 baud。固件请求 16 微步，运行 0.800 A RMS/相，保持 0.150 A。",
             (f"R10.2 <> {driver}.14",)),
    ])


ZONES = [
    Zone("input", "12 V 输入保护", "J1 接中心正极适配器。正接时电流经 F1 和 Q1 进入 V12，反接时 Q1 截止。", [
        ("插座、保险丝与防反接开关", (42, 17.8, 72, 40.6)),
    ], [
        Flow("正常供电", "jack:J1 中心正极 → fuse:F1 快熔 → switch:Q1 P 沟道 → rail:V12 母线",
             "体二极管先为输出充电，R1 将栅极拉低，Q1 随后导通。V12 经内层分配到降压器、两路电机和电磁铁。",
             ("J1.1 > F1.1", "F1.2 > Q1.5")),
        Flow("栅极保护", "rail:Q1 源极 → clamp:D1 齐纳 → io:Q1 栅极",
             "D1 阴极接源极、阳极接栅极。源栅电压差达到钳位值时，电流沿图示方向流动，限制栅氧化层承压。",
             ("Q1.2 > D1.1", "D1.2 > Q1.4")),
        Flow("母线浪涌", "rail:V12 尖峰 → clamp:D2 TVS → ground:GND",
             "D2 并联在 V12 与 GND 之间，尖峰时向地泄流。C1 同样跨在母线两端，负载突增时提供瞬时电流。"),
    ]),
    Zone("buck", "3.3 V 降压", "U1 将 12 V 斩波，L1 与 C4、C5 平滑输出。反馈分压设定典型输出 3.347 V。", [
        ("开关电流与输出取样", (8, -0.5, 22, 14)),
    ], [
        Flow("能量传递", "rail:V12 / C2 → switch:U1 上管 → inductor:L1 → rail:3.3 V",
             "上管导通时，电感电流上升并供给负载。C4、C5 并在输出端，吸收纹波。",
             ("C2.1 > U1.3", "U1.2 > L1.1", "L1.2 > C5.1")),
        Flow("关断后的续流", "ground:GND → switch:U1 下管 → inductor:L1 → load:负载",
             "连续导通时，上管关断、下管接通。电感保持原方向供电，电流逐渐下降并经负载回地。"),
        Flow("闭环取样", "rail:C5 输出 → resistor:R43 / R44 → io:U1 · FB",
             "R43 接输出、R44 接地，分压点接 FB。U1 调节导通时间，使 FB 接近 0.596 V。C35 跨 R43 加快瞬态响应。",
             ("C5.1 > R43.1", "R43.2 > U1.4")),
    ]),
    Zone("mcu", "主控与复位", "U2 运行 FluidNC，采样启动脚并输出运动命令。串口下载、复位和电机配置各有独立的信号路径。", [
        ("复位按键、ESP32 与串口接口", (2.5, -0.6, 54, 26.5)),
    ], [
        Flow("复位", "switch:SW1 按下 → io:ESP_EN 低 → chip:U2 复位",
             "SW1 闭合将 EN 接地，互锁随之关闭。松开后 R3 给 C8 充电。上电时还要等 U11 释放复位。",
             ("SW1.1 > U2.3",)),
        Flow("串口下载", "io:U4 DTR / RTS → switch:Q3 / Q4 → chip:U2 EN / IO0",
             "Q3 拉低 EN，Q4 拉低 GPIO0。复位释放时若 GPIO0 为低，ESP32 进入串口下载模式。",
             ("Q3.3 > U2.3", "Q4.3 > U2.25")),
        Flow("发出运动命令", "chip:U2 运算 → pulse:STEP / DIR → bridge:U5 / U6",
             "GPIO25/26 发往 U5，GPIO21/22 发往 U6。GPIO32 发出线圈 PWM，GPIO27 向互锁请求放行。",
             ("U2.10 > U5.16", "U2.33 > U6.16")),
        Flow("电机配置收发", "io:GPIO17 TX → resistor:R10 → io:TMC_BUS",
             "R10 串 1 kΩ 将发送端接入总线。回读从 TMC_BUS 经 R11（0 Ω）到 GPIO16 RX。",
             ("U2.28 > R10.1", "R11.1 > U2.27")),
    ]),
    Zone("usb", "USB-C 通信", "J2 接 USB 数据。板上 3.3 V 给 U4 和 ESP32 供电，USB 的 VBUS 用于检测主机。", [
        ("USB-C 插座至串口桥", (44.4, 3.2, 71.5, 21.1)),
    ], [
        Flow("USB 数据 · 双向", "jack:J2 D± ⇄ chip:U4 CP2102N",
             "D+、D− 从插座连到串口桥。U3 在插座旁给两线提供对地静电保护。",
             ("J2.A6 <> U3.3", "J2.A7 <> U3.4", "U3.3 <> U4.3", "U3.4 <> U4.4")),
        Flow("VBUS 检测", "rail:J2 VBUS → resistor:R29 / R30 → io:U4 VBUS",
             "R29 和 R30 将主机的 5 V 分压送到 U4 的 8 脚，主机移除后 R30 将检测脚拉低。",
             ("J2.A4 > R29.1", "R29.2 > U4.8")),
        Flow("串口收发", "chip:U4 TXD / RXD ⇄ io:交叉收发 ⇄ chip:U2 UART0",
             "U4 TXD 接 U2 RX。U2 TX 经 R28 接 U4 RXD。DTR/RTS 另送 Q3/Q4，控制复位与启动模式。",
             ("U4.21 > U2.34", "U2.35 > R28.1", "R28.2 > U4.20")),
    ]),
    Zone("lock", "执行器互锁", "U10 同时检查 ESP_EN 与 ARM。只有两者都为高，U9 才接通电机禁用命令和电磁铁命令。", [
        ("与非门与双缓冲器", (14.5, 19, 33.5, 34)),
        ("电源监控", (5.6, 0, 12.3, 8.8)),
        ("电机默认电平", (34.5, 25, 53.5, 40.5)),
    ], [
        Flow("上电与欠压", "rail:3.3 V → chip:U11 监控 → resistor:R40 → io:ESP_EN",
             "3.3 V 跌破典型 3.08 V 时，U11 拉低 EN。电压恢复后，典型延时 200 ms 才释放。",
             ("U11.2 > R40.1", "R40.2 > U10.2")),
        Flow("放行条件", "io:EN 与 ARM → nand:U10 与非 → io:ACT_OE_N → buffer:U9 使能",
             "EN、ARM 同为高时，ACT_OE_N 为低。其余组合让 U9 两路输出呈高阻，R35 使 ARM 上电默认为低。",
             ("U2.12 > U10.1", "U10.4 > U9.7")),
        Flow("两路受控输出", "chip:U2 命令 → buffer:U9 双缓冲 → io:ENN / SOL_SAFE",
             "U9 放行时传递 GPIO13、GPIO32。锁定时 R9 把 ENN 拉高，R22 把 Q7 基极拉低，电机与线圈均关闭。",
             ("U9.6 > U6.2", "U9.3 > R21.1")),
    ]),
    motor(True), motor(False),
    Zone("sol", "电磁铁输出", "GPIO32 的 PWM 经互锁驱动 Q7；Q7 拉低 Q6 栅极，将 12 V 接到 J5 的线圈正端。", [
        ("高侧开关、续流二极管与线圈端子", (0, 12.8, 25.8, 32.2)),
    ], [
        Flow("驱动栅极", "pulse:U9 · SOL_SAFE → resistor:R21 → switch:Q7 → io:Q6 栅极",
             "Q7 导通，经 R45 拉低 Q6 栅极。Q7 关断时，R33 将栅极拉回源极，使 Q6 截止。",
             ("U9.3 > R21.1", "R21.2 > Q7.1", "Q7.3 > R45.1", "R45.2 > Q6.4")),
        Flow("线圈通电", "rail:V12 → switch:Q6 → coil:J5-1 至线圈 → ground:J5-2 地",
             "Q6 源极接 V12，漏极接 J5-1。外接 12 V / 0.8 A 线圈经 J5-2 回地，通电时磁场逐渐建立。",
             ("Q6.5 > J5.1",)),
        Flow("关断后续流", "ground:J5-2 地 → diode:D4 → coil:J5-1 至线圈 → ground:J5-2 地",
             "Q6 关断后，电流由地经 D4 阳极流至阴极，再从 J5-1 穿过线圈回到 J5-2，直至磁场衰减。",
             ("J5.2 > D4.2", "D4.1 > J5.1")),
    ]),
    Zone("led", "指示灯", "五条并行支路分别指示电源、固件状态、线圈命令和端子电压。每条支路独立回地。", [
        ("逻辑电源", (3.7, 7.3, 11.3, 11.7)),
        ("串口桥下方的空闲与报警指示灯", (43, 12.7, 51.4, 20.7)),
        ("线圈命令", (17.4, 23.7, 24.2, 28.5)),
        ("线圈端电压", (2.8, 22.8, 11.1, 36.6)),
    ], [
        Flow(title, f"{kind}:{source} → resistor:{res} → led:{led} {colour} → ground:GND", note,
             (f"{res}.2 > {led}.2",))
        for title, kind, source, res, led, colour, note in [
            ("逻辑电源", "rail", "3.3 V", "R2", "D3", "绿", "D3 由 3.3 V 电源直接点亮，指示逻辑电源已建立。"),
            ("固件空闲", "io", "GPIO18", "R24", "D7", "绿", "GPIO18 为高时点亮。R26 将未驱动的 IDLE 线拉低。"),
            ("固件报警", "io", "GPIO19", "R25", "D8", "红", "GPIO19 为高时点亮。R27 将未驱动的 ALARM 线拉低。"),
            ("线圈命令", "pulse", "GPIO32", "R23", "D6", "黄", "D6 接互锁前的 SOL_CMD，反映主控发出的 PWM 请求。"),
        ]
    ] + [
        Flow("端子电压", "rail:J5-1 → resistor:R46 → led:D9 蓝 → ground:GND",
             "D9 接功率开关后的 SOL_POS。即使线圈拔下，端子有电压时仍会亮。",
             ("J5.1 > R46.1", "R46.2 > D9.2", "D9.1 > J5.2")),
    ]),
]

# Source-page crops (left, top, right, bottom in schematic millimetres).
# A functional area can span sheets: the ENN bias and power LED are examples.
SCHEMATICS = {
    "input": [(2, (17, 33, 201, 89), "入口保护")],
    "buck": [(2, (30, 108, 226, 169.5), "降压、滤波与反馈")],
    "mcu": [(3, (11, 26, 285, 166), "主控、复位与下载")],
    "usb": [(4, (12, 33, 287, 164), "USB 数据通路与 VBUS 检测")],
    "x": [(5, (16, 25, 271, 159), "X 驱动器与电机接口")],
    "y": [(6, (16, 25, 271, 159), "Y 驱动器与电机接口")],
    "sol": [(7, (16, 35, 281, 149), "高侧驱动与续流回路")],
    "lock": [(9, (13, 25, 281, 166), "硬件互锁"), (3, (85, 122, 119, 157), "ENN 上拉")],
    "led": [(8, (26, 44, 87, 125), "空闲"), (8, (113, 44, 174, 125), "报警"),
            (8, (211, 44, 285, 125), "命令与输出"), (2, (235, 103, 279, 158), "逻辑电源")],
}
