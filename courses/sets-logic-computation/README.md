# संच, तर्कशास्त्र, संगणन

रिचर्ड झॅक यांच्या *Sets, Logic, Computation* या पाठ्यपुस्तकाची मराठी आवृत्ती. तत्त्वज्ञान, गणित आणि संगणकशास्त्राच्या विद्यार्थ्यांसाठी हा औपचारिक अधितर्कशास्त्राचा परिचय आहे. पुस्तकात संच, संबंध आणि फलने; प्रथम-क्रम तर्कशास्त्राची विन्यासमीमांसा, चिन्हार्थमीमांसा व सिद्धतापद्धती; आणि ट्यूरिंग यंत्रे व संगणनक्षमता यांचा अभ्यास आहे. मुख्य मजकुरात १५ प्रकरणे, प्रकरणांचे १२ सारांश आणि सराव आहेत. परिशिष्टांत सिद्धतापद्धती, विगमन, चरित्रे आणि ग्रीक वर्णमाला आहेत. शेवटी ७९ नोंदींची पारिभाषिक शब्दसूची आणि संदर्भसूची दिली आहे.

- [संपूर्ण पुस्तक वाचा किंवा PDF उतरवा](https://github.com/KokunoYumeto/OpenLogic-mr-Deva-IN/raw/f8722cc37b93350e2f1b2e59d1b3fb783744e717/textbooks/slc/slc-screen-mr.pdf)
- [एकत्रित संपादनयोग्य LaTeX](https://github.com/KokunoYumeto/OpenLogic-mr-Deva-IN/raw/f8722cc37b93350e2f1b2e59d1b3fb783744e717/textbooks/slc/slc-screen-mr.tex)
- [संपूर्ण संपादनयोग्य स्रोतसंच व बांधणीसाठी आवश्यक सामग्री (ZIP)](https://github.com/KokunoYumeto/OpenLogic-mr-Deva-IN/raw/f8722cc37b93350e2f1b2e59d1b3fb783744e717/textbooks/slc/slc-source-mr.zip)
- [चित्रांचे व छायाचित्रांचे श्रेय](ASSET-CREDITS.md) · [मुद्राक्षरांचे श्रेय आणि परवाने](FONT-CREDITS.md) · [स्रोत व फाइल्सची नोंद](MANIFEST.json)

मूळ लेखक: Richard Zach. मूलग्रंथाची रचना आणि [Open Logic Project](https://openlogicproject.org/) च्या लेखकांनी व योगदानकर्त्यांनी दिलेला मजकूर यांचे श्रेय संबंधित निर्मात्यांना आहे. या आवृत्तीत [Open Logic च्या संपूर्ण मराठी आवृत्तीतील](https://github.com/KokunoYumeto/OpenLogic-mr-Deva-IN/releases/tag/complete-v1.2) विभाग वापरले आहेत. OpenAI Codex (GPT-6.1 Sol, Ultra) यांनी पाठ्यपुस्तकाच्या स्वतंत्र मजकुराचा मराठी यंत्रानुवाद व पुस्तकाची अक्षरजुळणी केली आहे. मूळ ग्रंथ आणि Open Logic मधून घेतलेल्या मजकुराला [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) लागू आहे. चित्रित व्यक्तिचित्रांना [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) लागू आहे; छायाचित्रांसाठी स्वतंत्र श्रेय व वापराच्या अटी पाहाव्यात. देवनागरी मुद्राक्षरे [SIL OFL 1.1](https://github.com/KokunoYumeto/OpenLogic-mr-Deva-IN/blob/f8722cc37b93350e2f1b2e59d1b3fb783744e717/textbooks/slc/fonts/OFL.txt) अंतर्गत आहेत.

प्रकल्पाचे प्रवर्तक, संपादक मंडळ आणि योगदानकर्त्यांची नावे पुस्तकाच्या आरंभी दिली आहेत. [Open Logic Project मधील श्रेयनिर्देश](https://openlogicproject.org/people/)

प्रथम-क्रम तर्कशास्त्रापलीकडील प्रकरण Jeremy Avigad यांच्या [*Logic and Computation*](https://www.andrew.cmu.edu/user/avigad/Teaching/landc_notes.pdf) (जानेवारी २००२, प्रकरण ८) या टिपणांवर आधारित आहे ([Open Logic मधील प्रकरण व त्याचे श्रेय](https://github.com/OpenLogicProject/OpenLogic/blob/9620cc73f9c8e0ad003c514a5d3748f29611c4c0/content/first-order-logic/beyond/beyond.tex)).

## PDF तयार करणे

स्रोतसंच एखाद्या स्वतंत्र निर्देशिकेत उलगडा. Python 3.10+, PowerShell 7, तसेच XeLaTeX, BibTeX, MakeIndex आणि पुस्तकासाठी लागणारी LaTeX पॅकेजेस असलेले अद्ययावत MiKTeX किंवा TeX Live आवश्यक आहेत. त्या निर्देशिकेतून चालवा:

```powershell
pwsh -NoProfile -File ./build.ps1
```

`build/` मधील नव्या `screen-*` निर्देशिकेत `slc-screen.pdf` मिळेल. `slc-screen.tex` हा मुख्य चालक आहे. `locale/mr/content/` मध्ये प्रकरणे आणि विभाग, `locale/mr/locale/` मध्ये स्थानिकीकरण, `locale/mr/config/` मध्ये पुस्तकाची मांडणी, आणि `include/` मध्ये प्रस्तावना, सारांश आणि शब्दसूची आहेत. समीकरणे व संदर्भ मूळ LaTeX नियंत्रणचिन्हांनी संपादित करता येतात. देवनागरी मजकुरासाठी स्रोतसंचातील Unicode मुद्राक्षरेच वापरली जातात; गणिताची दिशा डावीकडून उजवीकडे आहे. तिरप्या अक्षरांसाठी याच मुद्राक्षरांना XeLaTeX मध्ये किंचित कल दिला आहे. `गणनीय` या संज्ञेचा वापर मूळ पाठ्यपुस्तकातील *countable* आणि *enumerable* या दोन्हींसाठी केला आहे; *countably infinite* म्हणजे `गणनीय अनंत`.

```powershell
pwsh -NoProfile -File ./build.ps1 -Cumulative
```

दुसरी आज्ञा एकत्रित TeX मधील मजकूर नव्या बांधणी निर्देशिकेत उलगडते. त्या एकत्रित फाइलमध्ये केलेले संपादन या पद्धतीने PDF मध्ये दिसते. चित्रे, मुद्राक्षरे आणि इतर बांधणीसाहित्य दोन्ही पद्धतींसाठी स्रोतसंचात आहेत. शब्दसूचीचा मराठी वर्णक्रम स्रोतामधील निश्चित क्रमकळांनी जतन केला आहे; MakeIndex त्यांचा वापर करतो. [मूळ पाठ्यपुस्तक](https://slc.openlogicproject.org/) आणि [Open Logic Project चे मूळ स्रोत](https://github.com/OpenLogicProject/OpenLogic) स्वतंत्रपणे उपलब्ध आहेत.
