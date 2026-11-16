# मुक्त तर्कशास्त्र — संपूर्ण मराठी ग्रंथाचा संपादनयोग्य स्रोत

या ग्रंथात Open Logic Project च्या ७२२ स्रोत-एककांचे मराठी भाषांतर आहे. ७९ प्रकरणे आणि ६१३ विभाग एकत्र वाचण्यासाठी `build/full/openlogic-mr-full.tex` उघडा. एखाद्या प्रकरणाचा मजकूर संपादित करण्यासाठी त्याचा स्वतंत्र LaTeX खंड `chapter-sources/` मध्ये मिळेल. एककनिहाय मराठी मजकूर `mr/` मध्ये आहे. त्याच सापेक्ष मार्गावर `upstream/` मध्ये मूळ इंग्रजी मजकूर आहे.

मूळ ग्रंथाचे लेखक आणि योगदानकर्ते Open Logic Project चे आहेत. मराठी भाषांतर OpenAI Codex च्या GPT-5.6 Sol व GPT-6 Sol या मॉडेलांनी केले. GPT-6.1 Sol ने भाषांतरातील दुरुस्त्या आणि HTML व EPUB मधील अक्षरजुळणी व क्रमांकन केले. GPT-6 Astra ने बदललेल्या इंग्रजी एककांशी मराठी मजकूर जुळवला आणि ग्रंथाची अक्षरजुळणी केली. या चारही मॉडेलांसाठी Ultra तर्कप्रयत्न वापरले गेले. स्वतंत्र मानवी भाषिक पुनरावलोकन झालेले नाही.

मूळ ग्रंथ आणि भाषांतर Creative Commons Attribution 4.0 या परवान्याखाली उपलब्ध आहेत. परवान्याचा पूर्ण मजकूर `LICENSE.md` मध्ये आहे. अक्षररूपे आणि इतर स्वतंत्र घटकांसाठी त्यांच्यासोबत दिलेल्या परवाना-नोंदी पाहा. [मूळ इंग्रजी आवृत्ती](https://github.com/OpenLogicProject/OpenLogic/tree/a3862d07d2f5df3a281d4a55df73dcd59e84d5ce) · [मराठी आवृत्ती](https://github.com/KokunoYumeto/OpenLogic-mr-Deva-IN)

## PDF तयार करणे

Windows वर Python 3.11 किंवा त्यापुढील आवृत्ती, PowerShell 7 आणि XeLaTeX आवश्यक आहेत. संग्रह उलगडल्यानंतर त्याच्या मूळ निर्देशिकेतून पुढील आज्ञा चालवा.

```powershell
python -X utf8 tools/prepare_complete.py
python -X utf8 tools/qa_complete_reader.py
pwsh -NoProfile -File tools/build_guarded.ps1 -Target full
python -X utf8 tools/qa_complete_pdf.py
```

PDF `build/full/openlogic-mr-full.pdf` येथे मिळेल. एककनिहाय मजकूर बदलल्यावर `units.jsonl` मधील त्या एककाची नोंदही अद्ययावत करावी लागते. प्रत्येक प्रकरणाचा स्वतंत्र खंड हा संचयी LaTeX मधील उतारा आहे. एककांपासून पुन्हा ग्रंथ तयार करताना संपादन `mr/` मधील मूळ मराठी एककात करा.

## HTML आणि EPUB तयार करणे

यासाठी Pandoc आणि Python मधील PyMuPDF, Beautiful Soup 4 व lxml या लायब्रऱ्या आवश्यक आहेत. PDF तयार झाल्यावर पुढील आज्ञा चालवा.

नव्या आवृत्तीत आकृतीचे पान बदलले असेल, तर मागील प्रकाशित आवृत्तीच्या PDF व संचयी LaTeX फाइलवरून आकृत्यांची स्थाने पुन्हा तपासा. या तपासणीत प्रत्येक आकृतीचा आकार, तिच्यातील अक्षरे आणि प्रतिमा जुळणे आवश्यक आहे.

```powershell
python -X utf8 tools/locate_complete_diagrams.py --previous-tex PREVIOUS.tex --previous-pdf PREVIOUS.pdf
```

त्यानंतर HTML आणि EPUB तयार करा.

```powershell
python -X utf8 tools/complete_html_diagrams.py
python -X utf8 tools/prepare_complete_html.py
python -X utf8 tools/qa_complete_html.py
python -X utf8 tools/build_complete_epub.py publication/complete-epub-a3862d07.json
```

संगणकावर वाचण्यासाठी `build/full/html/index.html` उघडा. EPUB फाइल `build/epub-a3862d07/openlogic-mr-complete.epub` येथे मिळेल. EPUBCheck च्या JAR फाइलचा स्थानिक मार्ग देऊन EPUB तपासता येतो.

```powershell
python -X utf8 tools/qa_complete_epub.py publication/complete-epub-a3862d07.json --epubcheck-jar PATH/TO/epubcheck.jar
```
