

## 获取腾讯会议列表


curl 'https://meeting.tencent.com/wemeet-tapi/v2/meetlog/dashboard/my-record-list?c_app_id=&c_os_model=web&c_os=web&c_os_version=Mozilla%2F5.0%20(Macintosh%3B%20Intel%20Mac%20OS%20X%2010_15_7)%20AppleWebKit%2F537.36%20(KHTML%2C%20like%20Gecko)%20Chrome%2F150.0.0.0%20Safari%2F537.36&c_timestamp=1785423360324&c_nonce=zQn6jZsM3&c_app_version=&c_instance_id=5&c_account_corp_id=983619626&rnds=zQn6jZsM3&c_app_uid=&c_district=0&trace-id=dee515d108cd228a5ce09735eedcd386&c_lang=zh' \
  -H 'accept: application/json, text/plain, */*' \
  -H 'accept-language: en,en-US;q=0.9,zh-CN;q=0.8,zh;q=0.7' \
  -H 'content-type: application/json' \
  -b 'web_uid=ae5128b1-c8e4-4600-95d9-5b4e560c4d40; landing_url=https://meeting.tencent.com/; landing_path=https://meeting.tencent.com/; landing_referralurl=https://www.baidu.com/link?url=FpbaEX8GkWvqvG7VUnMrjEGGAXphnTf-Mp0tqtJYZEewNp49ctLO7pZeUqhiZ4u2&wd=&eqid=ed2a8c590188f682000000056a468075; landing_referraldomain=https://www.baidu.com; qcstats_seo_keywords=%E9%80%9A%E7%94%A8%E6%8A%80%E6%9C%AF-%E6%9C%8D%E5%8A%A1%E5%99%A8%E6%8A%80%E6%9C%AF-%E5%AE%B9%E5%99%A8%2C%E9%80%9A%E7%94%A8%E6%8A%80%E6%9C%AF-%E8%AE%A1%E7%AE%97-%E5%AE%B9%E5%99%A8%E9%95%9C%E5%83%8F%E6%9C%8D%E5%8A%A1; _gcl_au=1.1.874025170.1783119984; _qimei_uuid42=1a709061413100adb64b7f1ef8bbf49d56402e8eb3; _qimei_fingerprint=99c23d6c4b525324d131ffe1edbe491f; _qimei_q36=; _qimei_h38=9369a77bb64b7f1ef8bbf49d0300000f61a709; _qimei_i_3=42df6f87925355dc9493ab625d8575e9a6ebf6f31a590783e1dd285d2f93293d673065973989e28295a7; hy_anon_user=a_meeting_open_id_57d2c1f9a0924a30a547364bf0803c4a; hy_source=web; qcloud_visitId=c40c51af133b23e96337892e2e788cb4; qcloud_from=gwzcw.6688284.6688284.6688284-1784703208037; sensorsdata2015jssdkcross=%7B%22distinct_id%22%3A%22274210648%22%2C%22first_id%22%3A%2219f2a3b4443e21-0baf4d53a5d2118-16525631-2732424-19f2a3b4444179b%22%2C%22props%22%3A%7B%22%24latest_traffic_source_type%22%3A%22%E7%A4%BE%E4%BA%A4%E7%BD%91%E7%AB%99%E6%B5%81%E9%87%8F%22%2C%22%24latest_utm_medium%22%3A%22cps%22%7D%2C%22identities%22%3A%22eyIkaWRlbnRpdHlfY29va2llX2lkIjoiMTlmMmEzYjQ0NDNlMjEtMGJhZjRkNTNhNWQyMTE4LTE2NTI1NjMxLTI3MzI0MjQtMTlmMmEzYjQ0NDQxNzliIiwiJGlkZW50aXR5X2xvZ2luX2lkIjoiMjc0MjEwNjQ4In0%3D%22%2C%22history_login_id%22%3A%7B%22name%22%3A%22%24identity_login_id%22%2C%22value%22%3A%22274210648%22%7D%2C%22%24device_id%22%3A%2219f79282dc62977-0d18b8da90d2238-1f525630-2732424-19f79282dc73000%22%7D; _gcl_aw=GCL.1784703242.CjwKCAjwsfzSBhB5EiwAOGyqSdOxPE4DhjmsxmXdExEQLonGwfUa3rD6SZAvmZMp6pv-MbBegxi_tBoCVgcQAvD_BwE; _gcl_gs=2.1.k1$i1784703240$u140160097; corp_id=200000001; app_uid=16802000000036904232617; user_type=1; account_corp_id=983619626; we_meet_token=eJxUkVGTmjwYhf9Lbr-PGpIQiTO90O3utk7VWrqKe8MEiCQWAiYBrZ3*944szFruOOc5Sc77-gY-voYflLaO61TEKgNT4IP-O5XXddx0ikcDiODbhymDBGFEvUnP2exnfGM7dMC83hSXWhkR84MTBkwBhSSAsPdaYayqdJdCBAaI3JK9mTRWaWEtmIKzSHrRqVLc3jMJfA9i4g9wUeVKx*5XLTo8ldz1TiZaNRTrJSPyt1sDOjRQOZiCz6stquRa6Uu0j64kYqg4ONRK8eXEa1urssTM310fX*eSS2nO8rQJZ7gNi-C-cJIes6fxOHIyonhnLo0p6oL489nz9vtiPGufQsxXVi7kw-xl5kc0Y6uHzUswntjwCl*X68W3o4br7HiYoep4Xua7PdbL9daVycZt2r3LvZJF*lMu8DNZVI8f70Z-X*2kSqEwfRdqU2VN6v6BbPdzYBmnhMIRJUkyIilLRgx7aEQ5Tn0UZElyIO8BbO4O4GlaNdrFaWX6rbMAU49RNAy0scIM6-DAn78BAAD--7RPtos_; token_expire_time=1785708250; _ga_RPMZTEBERQ=GS2.1.s1785104218$o7$g0$t1785104228$j50$l0$h0; lz_sign=5UCEWfYbE_TTaOYm5p8l7JcgyduGWWQhVLCt7bJ55a93uC6ow8kkSwOAXxyFyf5CUQ0PNSZQOEZILO9PQ94XLFn2Hu6VCWAamNc8oc56V6A; lz_appid=200000001; lz_uid=16802000000036904232617; lz_time=1785421356772; _gid=GA1.2.1600648809.1785421358; _qimei_i_1=5bbd4c8b965c598ac690ac625d8021e7a1eff1a71a0951d4b0867c582593206c6163619339d8e5dcdfa0a0d9; hy_anon_token=8tE8bq6InCxff5mUqQZfc9aGHP6NPD80Cr/k258SiLJ0SRKVmpnUylkLLyDfCVTFh0OFyvytzHvdMXlQC27xkM/RfCjQVdDvUwDdwshdInKHX9DFMJW4CAnZWBE3mdsYtvbn1K/vk0Jn49rhl5uFbmJ+lS/e3SvOBk1pEyS9j1iTvFVPxdniZ9JNmG2sEPxf/MGQmlk/F0HbclVkmcIjB0KdfRAbq0sPfi9jfrq3qbJu0kMzQ11A/0q1d1GSvhjxQsZQnNmmIv2H9WahupdaPb/GPCAmbfXiADj0jISjcQ36OcRojjo35+uz8VNMKgROwyTRky/odKapo1lTXoeGeQ3CsaIvrKGf8OrEsaSuWZrLM/OR+dDyRrXeuY57nTWxTEgtHRLYmUr6ox1bPTgX56x+2OmKsSkjPZwGdkpSEpwyLCvTEpRYmnRtKgSpsRBuKCwJHEWSy5zQfdoOaVoMkv+J5Xj7VNRmSzLVrayzMSPKEX2MicIdxJ0peyC8EqwRWF1Fj8+n5bo1t6H8Xq5eXy/ePwX+5mDe7dFnhDfMoxtnc2hjllKE0Qlgqfp0oL2ww7nNyChng+HZcZrVoiaREBTh/um6OdjFKFn6XlohCt939ckkEQu5CtTZU8Cu4Bw3gtOvY06uNOSGLEYApryYcg==; _ga_6P1G7NCG3R=GS2.1.s1785421578$o7$g1$t1785421654$j57$l0$h395246300; _gat_UA-205111495-1=1; lz_expire=1785441351703; _ga=GA1.2.1203645289.1783005304; _ga_6WSZ0YS5ZQ=GS2.1.s1785421361$o18$g1$t1785423359$j50$l0$h0' \
  -H 'origin: https://meeting.tencent.com' \
  -H 'priority: u=1, i' \
  -H 'referer: https://meeting.tencent.com/user-center/meeting-record' \
  -H 'sec-ch-ua: "Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "macOS"' \
  -H 'sec-fetch-dest: empty' \
  -H 'sec-fetch-mode: cors' \
  -H 'sec-fetch-site: same-origin' \
  -H 'user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36' \
  -H 'web-caller: my_meetings' \
  --data-raw '{"begin_time":"0","end_time":"0","meeting_code":"","page_index":1,"page_size":10,"aggregationFastRecording":0,"cover_image_type":"meetlog_list_webp","record_type_v4":"fast_record|cloud_record|user_upload|realtime_transcription|voice_record","sort_by":"uni_record_id","record_scene":1}'


## 中间类型的会议记录，点开里面包含多个录频
https://meeting.tencent.com/user-center/shared-record-middle?s=sKOvc8uzP0m3wKeqOf4B4-dbRcitkw6MS48i412MBh4&from=0


### 中类类型会议记录列表
curl 'https://meeting.tencent.com/wemeet-tapi/v2/meetlog/record-detail/page-query-record-files?c_app_id=&c_os_model=web&c_os=web&c_os_version=Mozilla%2F5.0%20(Macintosh%3B%20Intel%20Mac%20OS%20X%2010_15_7)%20AppleWebKit%2F537.36%20(KHTML%2C%20like%20Gecko)%20Chrome%2F150.0.0.0%20Safari%2F537.36&c_timestamp=1785447217611&c_nonce=TbJPzsYC3&c_app_version=&c_instance_id=5&c_account_corp_id=983619626&rnds=TbJPzsYC3&c_app_uid=&c_district=0&trace-id=27e09424ce854060b77fdfb78d6b0b52&c_lang=zh' \
  -H 'accept: application/json, text/plain, */*' \
  -H 'accept-language: en,en-US;q=0.9,zh-CN;q=0.8,zh;q=0.7' \
  -H 'content-type: application/json' \
  -b 'web_uid=ae5128b1-c8e4-4600-95d9-5b4e560c4d40; landing_url=https://meeting.tencent.com/; landing_path=https://meeting.tencent.com/; landing_referralurl=https://www.baidu.com/link?url=FpbaEX8GkWvqvG7VUnMrjEGGAXphnTf-Mp0tqtJYZEewNp49ctLO7pZeUqhiZ4u2&wd=&eqid=ed2a8c590188f682000000056a468075; landing_referraldomain=https://www.baidu.com; qcstats_seo_keywords=%E9%80%9A%E7%94%A8%E6%8A%80%E6%9C%AF-%E6%9C%8D%E5%8A%A1%E5%99%A8%E6%8A%80%E6%9C%AF-%E5%AE%B9%E5%99%A8%2C%E9%80%9A%E7%94%A8%E6%8A%80%E6%9C%AF-%E8%AE%A1%E7%AE%97-%E5%AE%B9%E5%99%A8%E9%95%9C%E5%83%8F%E6%9C%8D%E5%8A%A1; _gcl_au=1.1.874025170.1783119984; _qimei_uuid42=1a709061413100adb64b7f1ef8bbf49d56402e8eb3; _qimei_fingerprint=99c23d6c4b525324d131ffe1edbe491f; _qimei_q36=; _qimei_h38=9369a77bb64b7f1ef8bbf49d0300000f61a709; _qimei_i_3=42df6f87925355dc9493ab625d8575e9a6ebf6f31a590783e1dd285d2f93293d673065973989e28295a7; hy_anon_user=a_meeting_open_id_57d2c1f9a0924a30a547364bf0803c4a; hy_source=web; qcloud_visitId=c40c51af133b23e96337892e2e788cb4; qcloud_from=gwzcw.6688284.6688284.6688284-1784703208037; sensorsdata2015jssdkcross=%7B%22distinct_id%22%3A%22274210648%22%2C%22first_id%22%3A%2219f2a3b4443e21-0baf4d53a5d2118-16525631-2732424-19f2a3b4444179b%22%2C%22props%22%3A%7B%22%24latest_traffic_source_type%22%3A%22%E7%A4%BE%E4%BA%A4%E7%BD%91%E7%AB%99%E6%B5%81%E9%87%8F%22%2C%22%24latest_utm_medium%22%3A%22cps%22%7D%2C%22identities%22%3A%22eyIkaWRlbnRpdHlfY29va2llX2lkIjoiMTlmMmEzYjQ0NDNlMjEtMGJhZjRkNTNhNWQyMTE4LTE2NTI1NjMxLTI3MzI0MjQtMTlmMmEzYjQ0NDQxNzliIiwiJGlkZW50aXR5X2xvZ2luX2lkIjoiMjc0MjEwNjQ4In0%3D%22%2C%22history_login_id%22%3A%7B%22name%22%3A%22%24identity_login_id%22%2C%22value%22%3A%22274210648%22%7D%2C%22%24device_id%22%3A%2219f79282dc62977-0d18b8da90d2238-1f525630-2732424-19f79282dc73000%22%7D; _gcl_aw=GCL.1784703242.CjwKCAjwsfzSBhB5EiwAOGyqSdOxPE4DhjmsxmXdExEQLonGwfUa3rD6SZAvmZMp6pv-MbBegxi_tBoCVgcQAvD_BwE; _gcl_gs=2.1.k1$i1784703240$u140160097; corp_id=200000001; app_uid=16802000000036904232617; user_type=1; account_corp_id=983619626; we_meet_token=eJxUkVGTmjwYhf9Lbr-PGpIQiTO90O3utk7VWrqKe8MEiCQWAiYBrZ3*944szFruOOc5Sc77-gY-voYflLaO61TEKgNT4IP-O5XXddx0ikcDiODbhymDBGFEvUnP2exnfGM7dMC83hSXWhkR84MTBkwBhSSAsPdaYayqdJdCBAaI3JK9mTRWaWEtmIKzSHrRqVLc3jMJfA9i4g9wUeVKx*5XLTo8ldz1TiZaNRTrJSPyt1sDOjRQOZiCz6stquRa6Uu0j64kYqg4ONRK8eXEa1urssTM310fX*eSS2nO8rQJZ7gNi-C-cJIes6fxOHIyonhnLo0p6oL489nz9vtiPGufQsxXVi7kw-xl5kc0Y6uHzUswntjwCl*X68W3o4br7HiYoep4Xua7PdbL9daVycZt2r3LvZJF*lMu8DNZVI8f70Z-X*2kSqEwfRdqU2VN6v6BbPdzYBmnhMIRJUkyIilLRgx7aEQ5Tn0UZElyIO8BbO4O4GlaNdrFaWX6rbMAU49RNAy0scIM6-DAn78BAAD--7RPtos_; token_expire_time=1785708250; _ga_RPMZTEBERQ=GS2.1.s1785104218$o7$g0$t1785104228$j50$l0$h0; _gid=GA1.2.1600648809.1785421358; _qimei_i_1=5bbd4c8b965c598ac690ac625d8021e7a1eff1a71a0951d4b0867c582593206c6163619339d8e5dcdfa0a0d9; hy_anon_token=8tE8bq6InCxff5mUqQZfc9aGHP6NPD80Cr/k258SiLJ0SRKVmpnUylkLLyDfCVTFh0OFyvytzHvdMXlQC27xkM/RfCjQVdDvUwDdwshdInKHX9DFMJW4CAnZWBE3mdsYtvbn1K/vk0Jn49rhl5uFbmJ+lS/e3SvOBk1pEyS9j1iTvFVPxdniZ9JNmG2sEPxf/MGQmlk/F0HbclVkmcIjB0KdfRAbq0sPfi9jfrq3qbJu0kMzQ11A/0q1d1GSvhjxQsZQnNmmIv2H9WahupdaPb/GPCAmbfXiADj0jISjcQ36OcRojjo35+uz8VNMKgROwyTRky/odKapo1lTXoeGeQ3CsaIvrKGf8OrEsaSuWZrLM/OR+dDyRrXeuY57nTWxTEgtHRLYmUr6ox1bPTgX56x+2OmKsSkjPZwGdkpSEpwyLCvTEpRYmnRtKgSpsRBuKCwJHEWSy5zQfdoOaVoMkv+J5Xj7VNRmSzLVrayzMSPKEX2MicIdxJ0peyC8EqwRWF1Fj8+n5bo1t6H8Xq5eXy/ePwX+5mDe7dFnhDfMoxtnc2hjllKE0Qlgqfp0oL2ww7nNyChng+HZcZrVoiaREBTh/um6OdjFKFn6XlohCt939ckkEQu5CtTZU8Cu4Bw3gtOvY06uNOSGLEYApryYcg==; _ga_6P1G7NCG3R=GS2.1.s1785421578$o7$g1$t1785421654$j57$l0$h395246300; lz_sign=wQWJNuPWXJcE4t5g2Wt0qQtMnKKmaqji02oNdPQj9RemA70UJCyo9LV-C_pkYXIQWp1iPVgdLBvev9n0zJcgfvzLPRrGEwywL6fXcTH41FE; lz_appid=200000001; lz_uid=16802000000036904232617; lz_time=1785447182092; _gat_UA-205111495-1=1; lz_expire=1785465209814; _ga=GA1.2.1203645289.1783005304; _ga_6WSZ0YS5ZQ=GS2.1.s1785447208$o19$g1$t1785447217$j51$l0$h0' \
  -H 'origin: https://meeting.tencent.com' \
  -H 'priority: u=1, i' \
  -H 'referer: https://meeting.tencent.com/user-center/shared-record-middle?s=sKOvc8uzP0m3wKeqOf4B4-dbRcitkw6MS48i412MBh4&from=0' \
  -H 'sec-ch-ua: "Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "macOS"' \
  -H 'sec-fetch-dest: empty' \
  -H 'sec-fetch-mode: cors' \
  -H 'sec-fetch-site: same-origin' \
  -H 'user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36' \
  -H 'web-caller: my_meetings' \
  --data-raw '{"page_index":1,"page_size":10,"cover_image_type":"meetlog_list_webp","encode_uni_recordId":"sKOvc8uzP0m3wKeqOf4B4-dbRcitkw6MS48i412MBh4"}'

{
  "code": 0,
  "err_detail": "",
  "msg": "",
  "data": {
    "records": [
      {
        "record_id": "2082584186595991553",
        "title": "录制1",
        "duration": "2096936",
        "cover_url": "https://wemeet-record-1258344699.file.myqcloud.com/cos/000011002000/1865959915521002082584/1865959915531002082584/2bfa2ae45a2359b7e9db46f9317cc2ee.png/mid?sign=ba025d7b92c256ad4d0feaaf349eecef\u0026t=1785447209",
        "sharing_id": "f20b8e70-8fc8-470b-81d2-e13df7129fc2",
        "minutes_paragraphs": [
          {
            "pid": "0",
            "sentences": [
              {
                "sid": "0",
                "words": [
                  {
                    "wid": "0",
                    "text": "大家早上好呀！"
                  }
                ]
              },
              {
                "sid": "1",
                "words": [
                  {
                    "wid": "1",
                    "text": "欢迎来到我们凡人晨读丰盛之流晨读营，"
                  }
                ]
              },
              {
                "sid": "2",
                "words": [
                  {
                    "wid": "2",
                    "text": "今天我们是第 19 天。"
                  }
                ]
              },
              {
                "sid": "3",
                "words": [
                  {
                    "wid": "3",
                    "text": "对，"
                  }
                ]
              },
              {
                "sid": "4",
                "words": [
                  {
                    "wid": "4",
                    "text": "今天已经是第 19 天了，"
                  }
                ]
              },
              {
                "sid": "5",
                "words": [
                  {
                    "wid": "5",
                    "text": "太快了，"
                  }
                ]
              },
              {
                "sid": "6",
                "words": [
                  {
                    "wid": "6",
                    "text": "对我们最近一直在聊，"
                  }
                ]
              },
              {
                "sid": "7",
                "words": [
                  {
                    "wid": "7",
                    "text": "我们在成都营可以训练什么，"
                  }
                ]
              },
              {
                "sid": "8",
                "words": [
                  {
                    "wid": "8",
                    "text": "那嗯有一个特别。"
                  }
                ]
              },
              {
                "sid": "9",
                "words": [
                  {
                    "wid": "9",
                    "text": "重要的一个方向，"
                  }
                ]
              },
              {
                "sid": "10",
                "words": [
                  {
                    "wid": "10",
                    "text": "就是我们可以把晨读营当成一个训练场来练习，"
                  }
                ]
              },
              {
                "sid": "11",
                "words": [
                  {
                    "wid": "11",
                    "text": "我们如何好好说话，"
                  }
                ]
              },
              {
                "sid": "12",
                "words": [
                  {
                    "wid": "12",
                    "text": "对，"
                  }
                ]
              },
              {
                "sid": "13",
                "words": [
                  {
                    "wid": "13",
                    "text": "好好说话，"
                  }
                ]
              },
              {
                "sid": "14",
                "words": [
                  {
                    "wid": "14",
                    "text": "其实还有一个很重要的前提，"
                  }
                ]
              },
              {
                "sid": "15",
                "words": [
                  {
                    "wid": "15",
                    "text": "就是能够很好的倾听以及很好的回应，"
                  }
                ]
              },
              {
                "sid": "16",
                "words": [
                  {
                    "wid": "16",
                    "text": "那试想一下我们在生活场景和工作场景啊，"
                  }
                ]
              },
              {
                "sid": "17",
                "words": [
                  {
                    "wid": "17",
                    "text": "很多时候呃，"
                  }
                ]
              },
              {
                "sid": "18",
                "words": [
                  {
                    "wid": "18",
                    "text": "我们会要去接对方说的话。"
                  }
                ]
              },
              {
                "sid": "19",
                "words": [
                  {
                    "wid": "19",
                    "text": "那对方一句话表达过来，"
                  }
                ]
              },
              {
                "sid": "20",
                "words": [
                  {
                    "wid": "20",
                    "text": "我们首先是否听见了，"
                  }
                ]
              },
              {
                "sid": "21",
                "words": [
                  {
                    "wid": "21",
                    "text": "然后我们听见了什么，"
                  }
                ]
              },
              {
                "sid": "22",
                "words": [
                  {
                    "wid": "22",
                    "text": "然后我们如何给予回应，"
                  }
                ]
              },
              {
                "sid": "23",
                "words": [
                  {
                    "wid": "23",
                    "text": "这个也是一个非常直接的练习，"
                  }
                ]
              },
              {
                "sid": "24",
                "words": [
                  {
                    "wid": "24",
                    "text": "好好说话的一个嗯。"
                  }
                ]
              },
              {
                "sid": "25",
                "words": [
                  {
                    "wid": "25",
                    "text": "对这样子的一个场景啊，"
                  }
                ]
              },
              {
                "sid": "26",
                "words": [
                  {
                    "wid": "26",
                    "text": "所以我就像我们昨天学习的内容啊，"
                  }
                ]
              }
            ],
            "speaker": {
              "user_id": "144115217804480614",
              "user_name": "康雯娟"
            }
          },
          {
            "pid": "1",
            "sentences": [
              {
                "sid": "27",
                "words": [
                  {
                    "wid": "27",
                    "text": "移情聆听就是当对方的这个语言表达过来的时候。"
                  }
                ]
              },
              {
                "sid": "28",
                "words": [
                  {
                    "wid": "28",
                    "text": "我们首先是否听见了对方在说什么，"
                  }
                ]
              },
              {
                "sid": "29",
                "words": [
                  {
                    "wid": "29",
                    "text": "是否听见了他的语言是什么？"
                  }
                ]
              },
              {
                "sid": "30",
                "words": [
                  {
                    "wid": "30",
                    "text": "这个其实是要求我们要有一定的专注力。"
                  }
                ]
              },
              {
                "sid": "31",
                "words": [
                  {
                    "wid": "31",
                    "text": "不然很多时候我们的呃心思如果很难拉回到当下，"
                  }
                ]
              },
              {
                "sid": "32",
                "words": [
                  {
                    "wid": "32",
                    "text": "可能我们呃，"
                  }
                ]
              },
              {
                "sid": "33",
                "words": [
                  {
                    "wid": "33",
                    "text": "当家人或者是同事跟我们讲话的时候，"
                  }
                ]
              },
              {
                "sid": "34",
                "words": [
                  {
                    "wid": "34",
                    "text": "可心已经跑到其他地方去了，"
                  }
                ]
              },
              {
                "sid": "35",
                "words": [
                  {
                    "wid": "35",
                    "text": "首先我们对这个他说的内容是听不见的。"
                  }
                ]
              },
              {
                "sid": "36",
                "words": [
                  {
                    "wid": "36",
                    "text": "这是第一层，"
                  }
                ]
              },
              {
                "sid": "37",
                "words": [
                  {
                    "wid": "37",
                    "text": "那如果我们只听见了内容，"
                  }
                ]
              },
              {
                "sid": "38",
                "words": [
                  {
                    "wid": "38",
                    "text": "我们的回应可能就是基于内容的，"
                  }
                ]
              },
              {
                "sid": "39",
                "words": [
                  {
                    "wid": "39",
                    "text": "但是呃，"
                  }
                ]
              },
              {
                "sid": "40",
                "words": [
                  {
                    "wid": "40",
                    "text": "如果只是基于内容的回应，"
                  }
                ]
              },
              {
                "sid": "41",
                "words": [
                  {
                    "wid": "41",
                    "text": "我们往往听不见他表达的真实意图，"
                  }
                ]
              },
              {
                "sid": "42",
                "words": [
                  {
                    "wid": "42",
                    "text": "也就是语言背后他。"
                  }
                ]
              },
              {
                "sid": "43",
                "words": [
                  {
                    "wid": "43",
                    "text": "带着一种什么样的情绪，"
                  }
                ]
              },
              {
                "sid": "44",
                "words": [
                  {
                    "wid": "44",
                    "text": "他有什么样的需要？"
                  }
                ]
              }
            ],
            "speaker": {
              "user_id": "144115217804480614",
              "user_name": "康雯娟"
            }
          },
          {
            "pid": "2",
            "sentences": [
              {
                "sid": "45",
                "words": [
                  {
                    "wid": "45",
                    "text": "这个大家在成都也讨论的也非常多啊，"
                  }
                ]
              },
              {
                "sid": "46",
                "words": [
                  {
                    "wid": "46",
                    "text": "我是否能够借由对方的语言表达的内容，"
                  }
                ]
              },
              {
                "sid": "47",
                "words": [
                  {
                    "wid": "47",
                    "text": "来去看见他当下的情绪，"
                  }
                ]
              },
              {
                "sid": "48",
                "words": [
                  {
                    "wid": "48",
                    "text": "看见他当下背后的需要。"
                  }
                ]
              },
              {
                "sid": "49",
                "words": [
                  {
                    "wid": "49",
                    "text": "那我们能听见这一层，"
                  }
                ]
              },
              {
                "sid": "50",
                "words": [
                  {
                    "wid": "50",
                    "text": "那我们又是否会在这层上去回应呢？"
                  }
                ]
              },
              {
                "sid": "51",
                "words": [
                  {
                    "wid": "51",
                    "text": "对，"
                  }
                ]
              },
              {
                "sid": "52",
                "words": [
                  {
                    "wid": "52",
                    "text": "那我们的这种回应啊，"
                  }
                ]
              },
              {
                "sid": "53",
                "words": [
                  {
                    "wid": "53",
                    "text": "更多的是一种说教，"
                  }
                ]
              },
              {
                "sid": "54",
                "words": [
                  {
                    "wid": "54",
                    "text": "还是一种陪伴呢？"
                  }
                ]
              },
              {
                "sid": "55",
                "words": [
                  {
                    "wid": "55",
                    "text": "那再进一步，"
                  }
                ]
              },
              {
                "sid": "56",
                "words": [
                  {
                    "wid": "56",
                    "text": "我们又是否能够听见情绪和需要啊，"
                  }
                ]
              },
              {
                "sid": "57",
                "words": [
                  {
                    "wid": "57",
                    "text": "背后，"
                  }
                ]
              },
              {
                "sid": "58",
                "words": [
                  {
                    "wid": "58",
                    "text": "它的缘起能够，"
                  }
                ]
              },
              {
                "sid": "59",
                "words": [
                  {
                    "wid": "59",
                    "text": "听见他为什么会有这样的情绪，"
                  }
                ]
              },
              {
                "sid": "60",
                "words": [
                  {
                    "wid": "60",
                    "text": "为什么会有这样的需要他的，"
                  }
                ]
              },
              {
                "sid": "61",
                "words": [
                  {
                    "wid": "61",
                    "text": "因在哪里？"
                  }
                ]
              },
              {
                "sid": "62",
                "words": [
                  {
                    "wid": "62",
                    "text": "我们能否看到这一层，"
                  }
                ]
              },
              {
                "sid": "63",
                "words": [
                  {
                    "wid": "63",
                    "text": "以及看见之后我们能否通过我们的善表达，"
                  }
                ]
              },
              {
                "sid": "64",
                "words": [
                  {
                    "wid": "64",
                    "text": "或者是我们的，"
                  }
                ]
              },
              {
                "sid": "65",
                "words": [
                  {
                    "wid": "65",
                    "text": "自己的这个以身作则的践行等等其他方式帮助他看见帮助他成长呢？"
                  }
                ]
              },
              {
                "sid": "66",
                "words": [
                  {
                    "wid": "66",
                    "text": "这个也是啊，"
                  }
                ]
              },
              {
                "sid": "67",
                "words": [
                  {
                    "wid": "67",
                    "text": "非常重要的能力啊，"
                  }
                ]
              },
              {
                "sid": "68",
                "words": [
                  {
                    "wid": "68",
                    "text": "昨天我们有几个伙伴和前辈在交流的时候也提到了这一点，"
                  }
                ]
              },
              {
                "sid": "69",
                "words": [
                  {
                    "wid": "69",
                    "text": "那这些其实啊是非常考验智慧的。"
                  }
                ]
              },
              {
                "sid": "70",
                "words": [
                  {
                    "wid": "70",
                    "text": "我相信在座各位大家都很希望自己成为一个有智慧的人，"
                  }
                ]
              },
              {
                "sid": "71",
                "words": [
                  {
                    "wid": "71",
                    "text": "那智慧从哪里来？"
                  }
                ]
              },
              {
                "sid": "72",
                "words": [
                  {
                    "wid": "72",
                    "text": "那我们听见的能力，"
                  }
                ]
              },
              {
                "sid": "73",
                "words": [
                  {
                    "wid": "73",
                    "text": "看见的能力如何善巧回应的能力。"
                  }
                ]
              },
              {
                "sid": "74",
                "words": [
                  {
                    "wid": "74",
                    "text": "这些都是属于智慧的一部分，"
                  }
                ]
              },
              {
                "sid": "75",
                "words": [
                  {
                    "wid": "75",
                    "text": "所以我们晨读有回应员的志愿者也有啊，"
                  }
                ]
              },
              {
                "sid": "76",
                "words": [
                  {
                    "wid": "76",
                    "text": "我们 21 天有一半的时间都是在回应的岗位，"
                  }
                ]
              }
            ],
            "speaker": {
              "user_id": "144115217804480614",
              "user_name": "康雯娟"
            }
          }
        ],
        "summary": "",
        "record_state": 3,
        "jump_path": "/meeting-record/shares?id=f20b8e70-8fc8-470b-81d2-e13df7129fc2\u0026from=12\u0026is-single=true\u0026record_type=2",
        "jump_path_short": "cw/Kmneejbq36",
        "is_record_backup": false,
        "audio_state": 1,
        "share_scope": 1,
        "allow_delete": true,
        "allow_download": true,
        "share_path_short": ""
      },
      {
        "record_id": "2082589889613090817",
        "title": "讨论组 01-录制1",
        "duration": "5591392",
        "cover_url": "https://wemeet-record-1258344699.file.myqcloud.com/cos/000011002000/1865959915521002082584/8896130908171002082589/2bfa2ae45a2359b7e9db46f9317cc2ee_shortcut.png/mid?sign=41fed2a5f8a1884717a5ca4478926c41\u0026t=1785447209",
        "sharing_id": "14906e39-0f89-4b57-909c-ebaaa5a27622",
        "minutes_paragraphs": [],
        "summary": "",
        "record_state": 3,
        "jump_path": "/meeting-record/shares?id=14906e39-0f89-4b57-909c-ebaaa5a27622\u0026from=12\u0026is-single=true\u0026record_type=2",
        "jump_path_short": "cw/KPj00JXW3c",
        "is_record_backup": false,
        "audio_state": 1,
        "share_scope": 1,
        "allow_delete": true,
        "allow_download": true,
        "share_path_short": ""
      },
      {
        "record_id": "2082589892988542977",
        "title": "讨论组 02-录制1",
        "duration": "5591200",
        "cover_url": "https://wemeet-record-1258344699.file.myqcloud.com/cos/000011002000/1865959915521002082584/8929885429771002082589/2bfa2ae45a2359b7e9db46f9317cc2ee_shortcut.png/mid?sign=466231886ae7fcb4c2f885312bd025b2\u0026t=1785447209",
        "sharing_id": "946f2e07-ecee-4e05-a7aa-98463caf2e32",
        "minutes_paragraphs": [],
        "summary": "",
        "record_state": 3,
        "jump_path": "/meeting-record/shares?id=946f2e07-ecee-4e05-a7aa-98463caf2e32\u0026from=12\u0026is-single=true\u0026record_type=2",
        "jump_path_short": "cw/NQoppeBW1c",
        "is_record_backup": false,
        "audio_state": 1,
        "share_scope": 1,
        "allow_delete": true,
        "allow_download": true,
        "share_path_short": ""
      }
    ],
    "b_jump_path": false,
    "uni_record_info": {
      "total_recording_size": "984175600",
      "total_view_counts": "2",
      "total_download_counts": "6",
      "uni_record_id": "2082584186595991552",
      "privilege_tips": "所有人需申请权限查看",
      "password": "",
      "recorder_username": "林泰君",
      "censor_state": 2,
      "recording_state": 3,
      "video_resolution_tag": "HD",
      "record_type": "cloud_record",
      "permission_type": 32,
      "password_switch": 0,
      "creator_uid": "16802000000036904232617",
      "total_backup_counts": "0"
    },
    "current_time": "1785447217883",
    "page_info": {
      "index": "1",
      "size": "10",
      "count": "3"
    },
    "meeting_info": {
      "subject": "5Liw55ub5LmL5rWBLee7n+WQiOe7vOaViA==",
      "meeting_code": "78442936167",
      "meeting_id": "13477124180492978577",
      "start_time": "1785361083000",
      "meeting_code_mask": "296",
      "meeting_type": 1,
      "meeting_kind": 1,
      "hybrid_meeting_type": 0
    },
    "meeting_members": [
      {
        "avatar_url": "https://meeting-75420.picgzc.qpic.cn/5317e81332ee835a31c5d9e0b08d13b31af0612b64447ac87664c29f4ddc6e13",
        "name": "筷筷"
      },
      {
        "avatar_url": "https://meeting-75420.picgzc.qpic.cn/6e6134c927b7298da9c624bf17e841daf1bffec39a07564cbaf2d2ac972ace8c",
        "name": "王可心"
      },
      {
        "avatar_url": "https://meeting-75420.picgzc.qpic.cn/7000d219155074eec5f876bf57698f16a208a65ca080bc946d7dc9b491af82b5",
        "name": "狮子"
      },
      {
        "avatar_url": "https://meeting-75420.picgzc.qpic.cn//fd46be7b091d199ba8f8ad3aa37eacd28ab6a3b7c048dfa0d2959052ec3ae7ff",
        "name": "张勐"
      },
      {
        "avatar_url": "https://meeting-75420.picgzc.qpic.cn/da6277c27f3e6abf9e2cc501352aad7faac683a03258e82826d29c49501a4071",
        "name": "林娜娜"
      },
      {
        "avatar_url": "https://meeting-75420.picgzc.qpic.cn//8873afd4565ff1d4f5f600c1d7e414b4ed35defa1ff8a598891b2a84477d79f7",
        "name": "林泰君"
      },
      {
        "avatar_url": "https://meeting-75420.picgzc.qpic.cn//ab3d0b75562bda7ce5b2b3811c3be85e588a32d540e01d7b4c79e529e15e9007",
        "name": "康雯娟"
      },
      {
        "avatar_url": "https://meeting-75420.picgzc.qpic.cn/418c3e884c9a705029aa1a5bd0bf7183af7114acb622580096ba5fcd49184e80",
        "name": "小凡"
      },
      {
        "avatar_url": "https://meeting-75420.picgzc.qpic.cn//f862cbcb02e0bd947be75fa884dd13fb7329e7973c76d5d86c969a6429dfc2c2",
        "name": "Ruinan瑞男"
      },
      {
        "avatar_url": "",
        "name": "悟因"
      },
      {
        "avatar_url": "",
        "name": "徐燕"
      },
      {
        "avatar_url": "https://meeting-75420.picgzc.qpic.cn//409c47812fda88407d1dce3e9900af738656e1b6ab0e5f719b71b755895e4f13",
        "name": "刘伟伟"
      },
      {
        "avatar_url": "https://meeting-75420.picgzc.qpic.cn/d11428d215359afed956dea763bf04f6a8dcd7415a3fa32dcb8f30ff80d713fb",
        "name": "赵敏慧"
      },
      {
        "avatar_url": "https://meeting-75420.picgzc.qpic.cn/9c8ca814f2989ebbaebf8fa60a775a09e35563e30c7d61f5962320bbfa8c84f0",
        "name": "张敏"
      },
      {
        "avatar_url": "https://meeting-75420.picgzc.qpic.cn/eddf11de3d59058b8df5fbc0e45bb65b08aa9c025441ee05de71c884082a59ad",
        "name": "伊娜"
      },
      {
        "avatar_url": "https://meeting-75420.picgzc.qpic.cn/ca6a7de18a4b75769bf0152ae093b3e424f114342324c673eee54787e0625b90",
        "name": "刘莎"
      },
      {
        "avatar_url": "https://meeting-75420.picgzc.qpic.cn/f2b682f20f50a4a01f2524f48fce42fd5a461e5145d48773241fcc5ab29df539",
        "name": "刘凤玲"
      }
    ],
    "sharing_id": "f50fc020-2678-4de8-b8ca-cdad680a4558",
    "jump_path": "/meeting-record/shares?id=f50fc020-2678-4de8-b8ca-cdad680a4558\u0026from=12\u0026is-single=false\u0026record_type=2",
    "jump_path_short": "cw/NxMXXn4Z16",
    "gray_aisummary_switch": 1,
    "gray_ai_topic_summary_switch": 1,
    "gray_ai_speaker_summary_switch": 1,
    "participant_num": 17,
    "gray_record_backup": 1,
    "gray_ai_template_summary_switch": 0,
    "share_path_short": "",
    "hit_qw_gray": false,
    "gray_ai_new_framework_switch": 1,
    "gray_ai_new_framework_ui_style": 1
  },
  "nonce": "9e549a88a01a8ec9d93bf29a9b882784",
  "timestamp": 1785447218
}

sharing_id 就是 每个字录制的 record_id, 根据 sharing_id 可以获得会议转录内容

## 会议转录内容

curl 'https://meeting.tencent.com/wemeet-cloudrecording-webapi/v1/minutes/detail?c_app_id=&c_os_model=web&c_os=web&c_os_version=Mozilla%2F5.0%20(Macintosh%3B%20Intel%20Mac%20OS%20X%2010_15_7)%20AppleWebKit%2F537.36%20(KHTML%2C%20like%20Gecko)%20Chrome%2F150.0.0.0%20Safari%2F537.36&c_timestamp=1785421648793&c_nonce=NKkzkrDmC&c_app_version=&c_instance_id=5&rnds=NKkzkrDmC&mock=1&platform=Web&c_app_uid=&c_district=0&c_account_corp_id=983619626&trace-id=0a4ba76de76d70d70a9997899d5e5f3b&id=14906e39-0f89-4b57-909c-ebaaa5a27622&pwd=&activity_uid=&page_source=record&meeting_id=13477124180492978577&recording_id=2082589889613090817&share_id=&short_url_code=&lang=zh&minutes_version=0&limit=20&return_ori=0&start_pid=0&return_ori_minutes_translating=1&fview=1' \
  -H 'accept: application/json, text/plain, */*' \
  -H 'accept-language: en,en-US;q=0.9,zh-CN;q=0.8,zh;q=0.7' \
  -b 'web_uid=ae5128b1-c8e4-4600-95d9-5b4e560c4d40; landing_url=https://meeting.tencent.com/; landing_path=https://meeting.tencent.com/; landing_referralurl=https://www.baidu.com/link?url=FpbaEX8GkWvqvG7VUnMrjEGGAXphnTf-Mp0tqtJYZEewNp49ctLO7pZeUqhiZ4u2&wd=&eqid=ed2a8c590188f682000000056a468075; landing_referraldomain=https://www.baidu.com; qcstats_seo_keywords=%E9%80%9A%E7%94%A8%E6%8A%80%E6%9C%AF-%E6%9C%8D%E5%8A%A1%E5%99%A8%E6%8A%80%E6%9C%AF-%E5%AE%B9%E5%99%A8%2C%E9%80%9A%E7%94%A8%E6%8A%80%E6%9C%AF-%E8%AE%A1%E7%AE%97-%E5%AE%B9%E5%99%A8%E9%95%9C%E5%83%8F%E6%9C%8D%E5%8A%A1; _gcl_au=1.1.874025170.1783119984; _qimei_uuid42=1a709061413100adb64b7f1ef8bbf49d56402e8eb3; _qimei_fingerprint=99c23d6c4b525324d131ffe1edbe491f; _qimei_q36=; _qimei_h38=9369a77bb64b7f1ef8bbf49d0300000f61a709; _qimei_i_3=42df6f87925355dc9493ab625d8575e9a6ebf6f31a590783e1dd285d2f93293d673065973989e28295a7; hy_anon_user=a_meeting_open_id_57d2c1f9a0924a30a547364bf0803c4a; hy_source=web; qcloud_visitId=c40c51af133b23e96337892e2e788cb4; qcloud_from=gwzcw.6688284.6688284.6688284-1784703208037; sensorsdata2015jssdkcross=%7B%22distinct_id%22%3A%22274210648%22%2C%22first_id%22%3A%2219f2a3b4443e21-0baf4d53a5d2118-16525631-2732424-19f2a3b4444179b%22%2C%22props%22%3A%7B%22%24latest_traffic_source_type%22%3A%22%E7%A4%BE%E4%BA%A4%E7%BD%91%E7%AB%99%E6%B5%81%E9%87%8F%22%2C%22%24latest_utm_medium%22%3A%22cps%22%7D%2C%22identities%22%3A%22eyIkaWRlbnRpdHlfY29va2llX2lkIjoiMTlmMmEzYjQ0NDNlMjEtMGJhZjRkNTNhNWQyMTE4LTE2NTI1NjMxLTI3MzI0MjQtMTlmMmEzYjQ0NDQxNzliIiwiJGlkZW50aXR5X2xvZ2luX2lkIjoiMjc0MjEwNjQ4In0%3D%22%2C%22history_login_id%22%3A%7B%22name%22%3A%22%24identity_login_id%22%2C%22value%22%3A%22274210648%22%7D%2C%22%24device_id%22%3A%2219f79282dc62977-0d18b8da90d2238-1f525630-2732424-19f79282dc73000%22%7D; _gcl_aw=GCL.1784703242.CjwKCAjwsfzSBhB5EiwAOGyqSdOxPE4DhjmsxmXdExEQLonGwfUa3rD6SZAvmZMp6pv-MbBegxi_tBoCVgcQAvD_BwE; _gcl_gs=2.1.k1$i1784703240$u140160097; corp_id=200000001; app_uid=16802000000036904232617; user_type=1; account_corp_id=983619626; we_meet_token=eJxUkVGTmjwYhf9Lbr-PGpIQiTO90O3utk7VWrqKe8MEiCQWAiYBrZ3*944szFruOOc5Sc77-gY-voYflLaO61TEKgNT4IP-O5XXddx0ikcDiODbhymDBGFEvUnP2exnfGM7dMC83hSXWhkR84MTBkwBhSSAsPdaYayqdJdCBAaI3JK9mTRWaWEtmIKzSHrRqVLc3jMJfA9i4g9wUeVKx*5XLTo8ldz1TiZaNRTrJSPyt1sDOjRQOZiCz6stquRa6Uu0j64kYqg4ONRK8eXEa1urssTM310fX*eSS2nO8rQJZ7gNi-C-cJIes6fxOHIyonhnLo0p6oL489nz9vtiPGufQsxXVi7kw-xl5kc0Y6uHzUswntjwCl*X68W3o4br7HiYoep4Xua7PdbL9daVycZt2r3LvZJF*lMu8DNZVI8f70Z-X*2kSqEwfRdqU2VN6v6BbPdzYBmnhMIRJUkyIilLRgx7aEQ5Tn0UZElyIO8BbO4O4GlaNdrFaWX6rbMAU49RNAy0scIM6-DAn78BAAD--7RPtos_; token_expire_time=1785708250; _ga_RPMZTEBERQ=GS2.1.s1785104218$o7$g0$t1785104228$j50$l0$h0; lz_sign=5UCEWfYbE_TTaOYm5p8l7JcgyduGWWQhVLCt7bJ55a93uC6ow8kkSwOAXxyFyf5CUQ0PNSZQOEZILO9PQ94XLFn2Hu6VCWAamNc8oc56V6A; lz_appid=200000001; lz_uid=16802000000036904232617; lz_time=1785421356772; _gid=GA1.2.1600648809.1785421358; _ga_6WSZ0YS5ZQ=GS2.1.s1785421361$o18$g1$t1785421557$j1$l0$h0; lz_expire=1785439560608; _qimei_i_1=6fe0498b965c598ac690ac625d8021e7a1eff1a71a0951d4b0867c582593206c6163619339d8e5dcdfaefbd9; hy_anon_token=8tE8bq6InCxff5mUqQZfc9aGHP6NPD80Cr/k258SiLJ0SRKVmpnUylkLLyDfCVTFh0OFyvytzHvdMXlQC27xkM/RfCjQVdDvUwDdwshdInKHX9DFMJW4CAnZWBE3mdsYtvbn1K/vk0Jn49rhl5uFbmJ+lS/e3SvOBk1pEyS9j1iTvFVPxdniZ9JNmG2sEPxfVbY451Zxl+fm2jbylgsz9oBgg0ib0K4/ne0wQFCMRaZI+YZeJoEOK8HNxgVF0DdY2w6WUuZ7nGctGuvykqrEI5kdWKMjkZ/HEdFPHGGBDzJJJ4wontwpkQkLkonbgvTgfZY3r2K7E84p8fhmDkOexizsdrZ+YIVTaiDdPD+BLG0P1fwdd5cnO10Rxd63QJKzLK8R5dmjntCsL2Y8rs3Q06huAdr8KMxViXkr637oSkP7zdPzEIf0KGCjZGf/UWI3oI2SiLGKwlYk23U36bq/bn7qv+JWyULVRGJ6TUzYt7l32xTnQctVwD170oAWN1R2XViCFZoteu/G6FVF2QEjGQkIvaefsRElwQMBpxZapPq6qr62ynNfQ6ZXmRMXNTMDT3y+ybpVY4Hcj8GYY8h46ukz6qFj3o/6YBOkpAt5MQXh8/lpsucDNcOwlcE1hatreS5Fth07Dj14m3YchE3HDw==; _ga=GA1.1.1203645289.1783005304; _ga_6P1G7NCG3R=GS2.1.s1785421578$o7$g0$t1785421578$j60$l0$h395246300' \
  -H 'priority: u=1, i' \
  -H 'referer: https://meeting.tencent.com/' \
  -H 'sec-ch-ua: "Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "macOS"' \
  -H 'sec-fetch-dest: empty' \
  -H 'sec-fetch-mode: cors' \
  -H 'sec-fetch-site: same-origin' \
  -H 'user-agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36'