# Uptown Assets: ระบบทำวิดีโอ TikTok สำหรับอสังหาริมทรัพย์

ระบบนี้ใช้ Claude Code ทำวิดีโอแนวตั้ง (9:16) สำหรับโพสต์ขายหรือเช่าทรัพย์บน TikTok ตั้งแต่อ่านข้อมูลประกาศ วางเรื่อง ทำเสียงพากย์ ไปจนถึงตัดต่อเป็นไฟล์ MP4 พร้อมโพสต์
งานแบ่งให้ AI หลายตัวทำตามหน้าที่ โดยมี **director** (ผู้กำกับ) เป็นตัวที่คุยกับเราและสั่งงานตัวอื่น

## ทีมงาน

| ชื่อ | ไฟล์ | หน้าที่ |
|---|---|---|
| **director** (role) | [.claude/roles/director.md](.claude/roles/director.md) | ผู้กำกับ เป็น role เริ่มต้นของโปรเจกต์ คุยกับเราเป็นภาษาไทย ถามข้อมูลที่ขาด วาง treatment และ shot list เขียน copy กับ caption สั่งงาน agent ด้านล่าง แล้วตรวจผลงานก่อนรายงาน |
| **brief** (agent) | [.claude/agents/brief.md](.claude/agents/brief.md) | อ่านข้อมูลประกาศ ตรวจรูปและคลิปทุกไฟล์ แยกตามห้อง ดึงข้อเท็จจริงของทรัพย์ แล้วเขียน `brief.md` (ความพร้อม, treatment ร่าง, สคริปต์เสียงพากย์, brief สำหรับ editor) |
| **voice-kanya** (agent) | [.claude/agents/voice-kanya.md](.claude/agents/voice-kanya.md) | ทำเสียงพากย์ภาษาไทยด้วยเสียง Kanya ของ macOS (`say`) ทำงานบนเครื่องทั้งหมด ฟรี แต่เสียงจะออกแนวหุ่นยนต์ ได้ไฟล์ `voiceover.wav` ที่ตรงกับไทม์ไลน์วิดีโอ |
| **editor-magnific** (agent) | [.claude/agents/editor-magnific.md](.claude/agents/editor-magnific.md) | เปลี่ยนรูปเป็นคลิปเคลื่อนไหวด้วย AI ของ Magnific (image-to-video เช่น Kling) ประเมินเครดิตก่อนและใช้ไม่เกินงบที่ director ให้ ตรวจทุกคลิปว่าไม่มีของงอก หาย หรือบิดเบี้ยว แล้วดาวน์โหลดมาไว้ให้ editor ตัดต่อ (ไม่ได้ตัดวิดีโอฉบับสุดท้ายเอง) |
| **editor** (agent) | [.claude/agents/editor.md](.claude/agents/editor.md) | ตัดต่อด้วย ffmpeg ทำเฉพาะวิดีโอ TikTok (1080×1920, 20–30 วินาที, ไม่เกิน 60) ใส่ Ken Burns, caption, เพลง และ end card แล้วตรวจไฟล์ก่อนส่ง |

## ขั้นตอนการทำวิดีโอ

1. **เตรียมไฟล์**: สร้างโฟลเดอร์ `listings/<รหัส>-<ชื่อทรัพย์>/assets/` แล้วใส่รูป คลิป โลโก้ และเพลง
2. **เปิดเซสชันในโปรเจกต์นี้**: role `director` จะถูกเลือกให้อัตโนมัติ บอกว่าทรัพย์คืออะไร ส่งข้อมูลประกาศ (ข้อความหรือไฟล์) และบอกโฟลเดอร์ assets
3. **ตอบคำถามของ director**: กลุ่มเป้าหมาย ความยาว โทน เพลง และต้องการเสียงพากย์ไหม (เสียง Kanya หรือไฟล์เสียงที่อัดเอง)
4. **agent `brief` เตรียมบรีฟ**: เขียน `listings/<ทรัพย์>/brief.md` แล้ว director ตรวจข้อเท็จจริงกับประกาศอีกรอบ
5. **อนุมัติ treatment**: director จะแสดง hook วินาทีแรก ลำดับเรื่อง shot list ข้อความบนจอ สคริปต์เสียงพากย์ และ end card ระบบจะยังไม่ทำงานชิ้นใหญ่จนกว่าเราจะตอบตกลง
6. **ทำเสียงพากย์** (ถ้าต้องการ): agent `voice-kanya` ทำ `voiceover.wav` แล้ว director ตั้งเวลา caption ตามเสียง
7. **คลิป AI จาก Magnific** (ถ้าต้องการ): director เสนอว่าช็อตไหนควรใช้คลิป AI พร้อมราคาเครดิต เมื่อเราตกลงช็อตและงบแล้ว agent `editor-magnific` จะทำคลิปไว้ใน `output/magnific/` ช็อตที่ไม่ผ่านการตรวจจะกลับไปใช้รูปแบบ Ken Burns
8. **ตัดต่อ**: agent `editor` สร้างวิดีโอใน `listings/<ทรัพย์>/output/` พร้อม `build.sh` ไว้สร้างซ้ำได้ ถ้าจะใส่เพลงเทรนด์ในแอป TikTok เอง ขอให้ทำ 2 เวอร์ชัน คือมีเพลงกับไม่มีเพลง (`_nomusic.mp4`)
9. **ตรวจและแก้**: director ตรวจไฟล์ (ความยาว ความละเอียด เสียง ข้อความอ่านออก) แล้วรายงาน ถ้าต้องแก้ก็สั่งตัดใหม่ได้

## โครงสร้างโฟลเดอร์ทรัพย์

```
listings/
  <รหัส>-<ชื่อทรัพย์>/
    assets/      รูป คลิป โลโก้ เพลง (ต้นฉบับ ระบบจะไม่แก้หรือลบ)
    brief.md     บรีฟจาก agent brief
    output/      วิดีโอที่ตัดเสร็จ, build.sh, voiceover.wav, voice/
```

ทุกอย่างใน `listings/` ถูกตั้งไว้ใน [listings/.gitignore](listings/.gitignore) ให้ไม่เข้า git (รวมถึง `brief.md` และวิดีโอที่ตัดเสร็จ) ต้องสำรองไฟล์เอง ทรัพย์ที่มีในเครื่องตอนนี้คือ `4269-manor-sanambinnam` และ `445-land-bang-yai`

## กฎที่ระบบยึด

- **ข้อเท็จจริงมาจากประกาศเท่านั้น**: ไม่แต่งราคา ขนาด หรือจุดเด่นเพิ่ม และไม่อ้างวิว ทิศ หรือสถานีใกล้เคียงถ้าประกาศไม่ได้ระบุ
- **ไม่แต่งรูปจนผิดจากของจริง**: ไม่ใช้ภาพ render หรือห้องตัวอย่างแทนห้องจริง
- **ข้อความบนจอเป็นภาษาไทย**: ราคาเขียนแบบ "5.5 ล้านบาท" พื้นที่ใช้ "ตร.ม." เบอร์โทรใช้รูปแบบ 0XX-XXX-XXXX และใช้คำว่า "รหัสทรัพย์"
- **Fair housing**: บรรยายตัวทรัพย์ ไม่ระบุว่าใครควรอยู่
- **ลิขสิทธิ์**: ใช้เฉพาะเพลง รูป และฟุตเทจที่มีสิทธิ์ใช้ ถ้าไม่ชัด (เช่นภาพหน้าจอ Google Maps) ระบบจะแจ้งก่อน
- **Caption ฝังในวิดีโอเสมอ** เพราะคนดูจำนวนมากปิดเสียง

## สิ่งที่ต้องมีในเครื่อง

- Claude Code (แอปเดสก์ท็อปหรือเทอร์มินัล) เวอร์ชัน 2.1.286 ขึ้นไป
- `ffmpeg` และ `ffprobe`
- macOS ที่มีเสียง Kanya (สำหรับเสียงพากย์ภาษาไทย)
- บัญชี Magnific แบบเสียเงินที่เชื่อมกับ Claude เป็น connector (เฉพาะถ้าจะใช้ agent `editor-magnific`)

---

## ปลั๊กอินพื้นฐาน: shanti-roles

ระบบ role ข้างบนทำงานด้วยปลั๊กอินที่ก๊อปมาจาก [MrLudy-BxB/shanti-roles](https://github.com/MrLudy-BxB/shanti-roles)

| ปลั๊กอิน | หน้าที่ |
|---|---|
| **session-role** | ให้แต่ละเซสชันมี Role (หน้าที่ของ Claude) เลือกได้จาก dropdown เหนือช่องแชท หรือพิมพ์ `/role <ชื่อ>` แสดงสถานะการทำงานและ subagent ที่กำลังทำงาน |
| **usage-band** | แถบเหนือช่องแชท แสดงว่า context และโควตาการใช้งานของรอบนี้และของสัปดาห์เหลือเท่าไร |

ติดตั้ง:

```bash
claude plugin marketplace add MrLudy-BxB/shanti-roles
claude plugin install session-role@shanti-roles
claude plugin install usage-band@shanti-roles
```

รายละเอียดเพิ่มเติมอยู่ใน [session-role/README.md](session-role/README.md) และ [session-role/ARCHITECTURE.md](session-role/ARCHITECTURE.md)

```
.claude-plugin/marketplace.json   แคตตาล็อกปลั๊กอิน (marketplace "shanti-roles")
session-role/                     ปลั๊กอิน role, ตัวเลือก role, ขอบเขตการแก้ไฟล์, ตัวแสดง subagent
usage-band/                       ปลั๊กอินแถบแสดงการใช้งาน
export.py                         เครื่องมือสำหรับ export ปลั๊กอินจากโฟลเดอร์ dev
```
