# HELLDIVERSBOT

A QQ bot to fetch Helldivers 2 Companion data everywhere. Based on **helldiversbot**.

## Active places
在私聊中直接使用 */命令*调用

在群聊中使用 *@机器人 /命令*调用

## Fast Manual
|Command|Parameter|Description|Web API|
|--|--|--|---|
|/p or /planet|`<planetname>`or`<index>`|planet data|`/api/v1/planets/<index>?mode=md`|
|/d or /dispatch|No need|Current Dispatch|`/api/v1/dispatches?mode=md`|
|/t or /trending|No need|Planets have most players||

### Example:
`/p BEKVAM III`

```plaintext
星球名：BEKVAM III
分区：NANOS
所属阵营：机器人
已防御：6.2964%
预测：失败
剩余时间：15小时56分
部署的绝地潜兵数：12888
数据获取时间：2026-09-14T03:16:56.8288321Z
```