# throb-shrine-search-api
## 概要
周辺の神社を検索するAPI

## API
* Master
 * 緯度経度より周辺の神社を検索
* Zipcode
 * 郵便番号で周辺の神社を検索


## DB構成
|bucket_type  |bucket   |key            |Value             |Desc             |
|------------:|:--------|:--------------|:----------------|:----------------|
|shrine       |master   |<*shrine_id*>  |{}   |各神社の基本情報   |
|shrine       |zipcode  |<*zip_code*>   |{}  |郵便番号の緯度経度  |

