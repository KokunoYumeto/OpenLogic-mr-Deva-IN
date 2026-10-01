# संपूर्ण निर्णय-JSON

GitHub च्या एका फाइलच्या आकारमर्यादेमुळे संपूर्ण निर्णय-JSON येथे [`DECISIONS.json.gz`](DECISIONS.json.gz) या अचूक संकुचित रूपात आहे. ती उघडल्यावर `DECISIONS.json` ही प्रमाणित फाइल मिळते. [पुनरावलोकन-संग्रहात](https://github.com/KokunoYumeto/OpenLogic-mr-Deva-IN/releases/download/complete-v1.2/05-openlogic-mr-complete-review.zip) आणि [संपूर्ण स्रोत-संग्रहात](https://github.com/KokunoYumeto/OpenLogic-mr-Deva-IN/releases/download/complete-v1.2/03-openlogic-mr-complete-editable-sources.zip) तिची असंकुचित प्रत आहे.

Python वापरून असंकुचित प्रत तयार करण्यासाठी या निर्देशिकेतून चालवा:

```sh
python -c "import gzip,pathlib; pathlib.Path('DECISIONS.json').write_bytes(gzip.open('DECISIONS.json.gz','rb').read())"
```

असंकुचित फाइलचा SHA-256: `0956ad84fddab74e890cdbe5b6c27261674bc6c3855adcc1307820e22bab6aae`. दोन्ही रूपांची ओळख व वाचक-PDF चा हॅश [`CANONICAL_JSON_DOWNLOAD.json`](CANONICAL_JSON_DOWNLOAD.json) मध्ये आहेत.
