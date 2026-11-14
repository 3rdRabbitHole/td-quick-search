# TD Quick Search

TouchDesigner 的精簡版節點搜尋工具。按下快捷鍵,在滑鼠位置跳出一行搜尋列,
打幾個字、按 Enter,節點就放在滑鼠原本的位置。

A minimal operator search popup for TouchDesigner. Press the shortcut, type a few
letters, press Enter: the operator is created where the mouse was.

- 一開始只有一行搜尋列和一排家族標籤,輸入 2 個字以上才列出結果
- 同名節點合併成一列(例如 Noise),可用的家族標籤會亮起,用左右鍵挑家族
- 支援縮寫:`mfo` 或 `m f o` 都能找到 Movie File Out
- 放下的節點可以用 Ctrl+Z 復原
- 僅支援 Windows

## 安裝 / Install

1. 下載這個資料夾。
2. 在 TouchDesigner 開啟 Textport(Alt+T),執行下面這行,把 `<path>` 換成資料夾路徑:

   ```python
   src = r'<path>'; exec(open(src + '/build_quick_search.py', encoding='utf-8').read())
   ```

這會在專案根層建立 `/quick_search` 元件。元件建好後不再依賴這些檔案,
可以另存成 `.tox`,拖進其他專案的根層使用。重新執行同一行會重建元件。

## 使用方式 / Usage

滑鼠停在 network editor 上:

| 按鍵 | 動作 |
| --- | --- |
| Ctrl+Tab | 開啟 / 關閉搜尋列 |
| 打字 | 搜尋(2 個字以上) |
| ↑ / ↓ | 選節點 |
| ← / → 或 Tab / Shift+Tab | 在亮起的家族之間切換 |
| Enter | 把節點放在開啟搜尋列時的滑鼠位置 |
| Esc 或點擊其他地方 | 關閉 |

也可以直接點結果列,或點亮起的家族標籤來放下節點。

預設家族:有選取節點時跟它同家族,否則是上一次放下的家族。

## 設定 / Settings

| 位置 | 名稱 | 預設 | 說明 |
| --- | --- | --- | --- |
| `build_quick_search.py` | `SHORTCUT` | `ctrl.tab` | 開啟搜尋列的快捷鍵 |
| `QuickSearchExt.py` | `MIN_CHARS` | `2` | 開始搜尋所需的最少字數 |
| `QuickSearchExt.py` | `MAX_ROWS` | `8` | 最多顯示幾列結果(兩個檔案裡的值要一致) |

修改後重新執行安裝那一行即可。

## 運作方式 / How it works

節點清單來自 TouchDesigner 內建的 `families`,所以新版本新增的節點會自動出現。
搜尋列是一個取得鍵盤焦點的文字欄:編輯文字時 TouchDesigner 會把按鍵交給文字欄,
network editor 的快捷鍵(Backspace 刪除、`d` 切換 display、Tab 開啟 OP Create 選單等)
就不會在打字時被觸發。

## 已知限制 / Limitations

- 僅支援 Windows;只在 TouchDesigner 2025.30000 系列、100% 顯示縮放下測試過。
- 節點位置是由滑鼠的螢幕座標換算的,TouchDesigner 視窗邊框厚度假設為 8 像素。
- 清單包含所有節點,不會依授權或作業系統過濾。
- 只會把節點放在滑鼠位置,不會自動接線。

## 授權 / License

[MIT](LICENSE)
