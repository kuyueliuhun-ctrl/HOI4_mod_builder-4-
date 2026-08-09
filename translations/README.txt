# 翻译文件目录

将翻译文件拖入此文件夹，程序启动时会自动加载。

## 支持的文件格式

### 1. JSON 翻译文件 (*.json)
简单键值对格式：
```json
{
    "english_key": "中文翻译",
    "another_key": "另一个翻译"
}
```

### 2. HOI4 本地化文件 (*_l_simp_chinese.yml)
标准 HOI4 YAML 格式：
```yaml
l_simp_chinese:
  MY_MODIFIER: "我的修正器"
  MY_FOCUS: "我的国策"
```

### 3. 自定义语句文件 (含 statements 的 JSON)
```json
{
    "statements": [
        {
            "key": "my_effect",
            "cn_name": "我的效果",
            "node_type": "value",
            "default_value": "",
            "value_translations": {},
            "description": ""
        }
    ]
}
```

## 使用方法

1. 将翻译文件复制/拖入此文件夹
2. 重启程序，翻译自动生效
3. 或在程序中调用 `translator.load_translations_folder()` 重新扫描
