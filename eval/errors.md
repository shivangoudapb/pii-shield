# Hybrid PERSON/LOCATION errors

Each item below is a test-set miss or false alarm. Raw dataset text appears here by design, as explicitly requested for error analysis.

## common-word names

- Miss | item t001 | text: 'Resume contact • Hope Bhat | mobile +91 78317 44591 | mail sample603000@example.com — follow up with Hope | non-Aadhaar 12-digit ref 511591098810' | expected: 'Hope' [101:105 PERSON] | detected: none
- Miss | item t004 | text: 'Address card for Kulkarni, Kiran: 41 Lotus Lane, Test Garden, Hyderabad, 913681 | locker reference 316928' | expected: '41 Lotus Lane, Test Garden, Hyderabad' [34:71 LOCATION] | detected: none
- Miss | item t013 | text: 'Education row — Faith Yarlagadda; call +91 76629 17385 after 6pm (nickname Faiy) | email sales012@okhdfcbank.com' | expected: 'Faiy' [75:79 PERSON] | detected: none
- Miss | item t037 | text: 'From: Kiran\nneed the form today\nmail sample603036@example.com; full record: Kiran Mitra | non-Aadhaar 12-digit ref 478085606140' | expected: 'Kiran' [6:11 PERSON] | detected: none
- Miss | item t049 | text: 'group: Preeti Modi and Kiran Grewal are sharing PAN WKFAP7599K here — follow up with Preeti | email sales048@okhdfcbank.com' | expected: 'Preeti' [85:91 PERSON] | detected: none
- Miss | item t058 | text: 'Billed party: Ravi Hegde\nDelivery: 96 Maple Road, Sample Nagar, Hyderabad, 240416\nPAN WWDBI5459F | locker reference 551496' | expected: '96 Maple Road, Sample Nagar, Hyderabad' [35:73 LOCATION] | detected: '96 Maple Road, Sample Nagar' [35:62 LOCATION]
- False alarm | item t058 | text: 'Billed party: Ravi Hegde\nDelivery: 96 Maple Road, Sample Nagar, Hyderabad, 240416\nPAN WWDBI5459F | locker reference 551496' | expected: '96 Maple Road, Sample Nagar, Hyderabad' [35:73 LOCATION] | detected: '96 Maple Road, Sample Nagar' [35:62 LOCATION]
- False alarm | item t058 | text: 'Billed party: Ravi Hegde\nDelivery: 96 Maple Road, Sample Nagar, Hyderabad, 240416\nPAN WWDBI5459F | locker reference 551496' | expected: '96 Maple Road, Sample Nagar, Hyderabad' [35:73 LOCATION] | detected: 'Hyderabad' [64:73 LOCATION]
- Miss | item t061 | text: 'Ship to Anand Amin at 59 Amber Cross, Practice Colony, Bengaluru, 967855 (nickname Anay) | order ref 5463776206' | expected: '59 Amber Cross, Practice Colony, Bengaluru' [22:64 LOCATION] | detected: none
- Miss | item t079 | text: 'Regards,\nBose, Pinky\nOffice contact sample603078@example.com | order ref 3743482793' | expected: 'Bose, Pinky' [9:20 PERSON] | detected: 'Bose' [9:13 PERSON]
- False alarm | item t079 | text: 'Regards,\nBose, Pinky\nOffice contact sample603078@example.com | order ref 3743482793' | expected: 'Bose, Pinky' [9:20 PERSON] | detected: 'Bose' [9:13 PERSON]
- False alarm | item t079 | text: 'Regards,\nBose, Pinky\nOffice contact sample603078@example.com | order ref 3743482793' | expected: 'Bose, Pinky' [9:20 PERSON] | detected: 'Pinky' [15:20 PERSON]
- Miss | item t085 | text: 'College circular — Mukta; contact +91 65664 18184 for details; full record: Mukta Alluri | email sales084@okhdfcbank.com' | expected: 'Mukta' [19:24 PERSON] | detected: none
- False alarm | item t088 | text: 'Event registration: Leela Khan / sample603087@example.com / PAN JHUMD0913U | playlist title: ‘Sample Nagar’ (not an address)' | expected: none | detected: 'Sample Nagar' [94:106 LOCATION]
- Miss | item t097 | text: 'Hostel update for Ocean Chatterjee — UPI payee603096@okhdfcbank for meal plan — follow up with Ocean | order ref 5011135907' | expected: 'Ocean' [95:100 PERSON] | detected: none

## initials

- Miss | item t041 | text: 'group: H. F. Nayak and Charan Chowdary are sharing PAN FNJUY3994P here (surname on roster: Nayak)' | expected: 'Nayak' [91:96 PERSON] | detected: none
- Miss | item t057 | text: 'Remit to payee603056@okhdfcbank; billing contact H. Q. Khan at sample603056@example.com (surname on roster: Khan)' | expected: 'Khan' [108:112 PERSON] | detected: none
- Miss | item t073 | text: 'Remit to payee603072@okhdfcbank; billing contact S. Q. Subramanian at sample603072@example.com (surname on roster: Subramanian) | non-Aadhaar 12-digit ref 758884955160' | expected: 'Subramanian' [115:126 PERSON] | detected: none
- Miss | item t089 | text: 'Hostel update for V. M. Dhillon — UPI payee603088@okhdfcbank for meal plan (surname on roster: Dhillon)' | expected: 'Dhillon' [95:102 PERSON] | detected: none

## lowercase

- Miss | item t030 | text: 'hii nikhita reddy 😅 pls send UPI payee603029@okhdfcbank when u can' | expected: 'nikhita reddy' [4:17 PERSON] | detected: 'hii nikhita reddy' [0:17 PERSON]
- False alarm | item t030 | text: 'hii nikhita reddy 😅 pls send UPI payee603029@okhdfcbank when u can' | expected: 'nikhita reddy' [4:17 PERSON] | detected: 'hii nikhita reddy' [0:17 PERSON]

## regional names

- None.

## company-name lookalikes

- Miss | item t028 | text: 'bhai F Gokhale ka contact 8237715316 hai, send msg when free | vendor company Arjun Foods' | expected: 'F Gokhale' [5:14 PERSON] | detected: 'bhai F Gokhale' [0:14 PERSON]
- False alarm | item t028 | text: 'bhai F Gokhale ka contact 8237715316 hai, send msg when free | vendor company Arjun Foods' | expected: 'F Gokhale' [5:14 PERSON] | detected: 'bhai F Gokhale' [0:14 PERSON]
- Miss | item t046 | text: 'hii rani nadar 😅 pls send UPI payee603045@okhdfcbank when u can | vendor company Lakshmi Textiles' | expected: 'rani nadar' [4:14 PERSON] | detected: 'hii rani nadar' [0:14 PERSON]
- False alarm | item t046 | text: 'hii rani nadar 😅 pls send UPI payee603045@okhdfcbank when u can | vendor company Lakshmi Textiles' | expected: 'rani nadar' [4:14 PERSON] | detected: 'hii rani nadar' [0:14 PERSON]

## boundary errors

- Miss | item t003 | text: 'Candidate N Patel / PAN ILPQA2151D / phone 90680-87035' | expected: 'N Patel' [10:17 PERSON] | detected: 'Candidate N Patel' [0:17 PERSON]
- False alarm | item t003 | text: 'Candidate N Patel / PAN ILPQA2151D / phone 90680-87035' | expected: 'N Patel' [10:17 PERSON] | detected: 'Candidate N Patel' [0:17 PERSON]
- Miss | item t012 | text: 'Address card for Saxena, Aarav: 19 Amber Cross, Model Extension, Indore, 245796' | expected: '19 Amber Cross, Model Extension, Indore' [32:71 LOCATION] | detected: 'Indore' [65:71 LOCATION]
- False alarm | item t012 | text: 'Address card for Saxena, Aarav: 19 Amber Cross, Model Extension, Indore, 245796' | expected: '19 Amber Cross, Model Extension, Indore' [32:71 LOCATION] | detected: 'Indore' [65:71 LOCATION]
- Miss | item t019 | text: 'Candidate N Venkataraman / PAN DVEGY9510Q / phone 99643-44868 | non-Aadhaar 12-digit ref 216480279760' | expected: 'N Venkataraman' [10:24 PERSON] | detected: 'Candidate N Venkataraman' [0:24 PERSON]
- False alarm | item t019 | text: 'Candidate N Venkataraman / PAN DVEGY9510Q / phone 99643-44868 | non-Aadhaar 12-digit ref 216480279760' | expected: 'N Venkataraman' [10:24 PERSON] | detected: 'Candidate N Venkataraman' [0:24 PERSON]
- Miss | item t020 | text: 'Address card for Chettiar, Bhavani: 38 Amber Cross, Sample Nagar, Surat, 898137' | expected: '38 Amber Cross, Sample Nagar, Surat' [36:71 LOCATION] | detected: '38 Amber Cross, Sample Nagar' [36:64 LOCATION]
- False alarm | item t020 | text: 'Address card for Chettiar, Bhavani: 38 Amber Cross, Sample Nagar, Surat, 898137' | expected: '38 Amber Cross, Sample Nagar, Surat' [36:71 LOCATION] | detected: '38 Amber Cross, Sample Nagar' [36:64 LOCATION]
- False alarm | item t020 | text: 'Address card for Chettiar, Bhavani: 38 Amber Cross, Sample Nagar, Surat, 898137' | expected: '38 Amber Cross, Sample Nagar, Surat' [36:71 LOCATION] | detected: 'Surat' [66:71 LOCATION]
- Miss | item t036 | text: 'bhai Y Awasthi ka contact 6819743243 hai, send msg when free' | expected: 'Y Awasthi' [5:14 PERSON] | detected: 'bhai Y Awasthi' [0:14 PERSON]
- False alarm | item t036 | text: 'bhai Y Awasthi ka contact 6819743243 hai, send msg when free' | expected: 'Y Awasthi' [5:14 PERSON] | detected: 'bhai Y Awasthi' [0:14 PERSON]
- Miss | item t044 | text: 'bhai R Shaikh ka contact 9666394023 hai, send msg when free' | expected: 'R Shaikh' [5:13 PERSON] | detected: 'bhai R Shaikh' [0:13 PERSON]
- False alarm | item t044 | text: 'bhai R Shaikh ka contact 9666394023 hai, send msg when free' | expected: 'R Shaikh' [5:13 PERSON] | detected: 'bhai R Shaikh' [0:13 PERSON]
- Miss | item t066 | text: 'Billed party: Senthil Iyer\nDelivery: 59 Amber Cross, Practice Colony, Pune, 317283\nPAN XONCN2797D' | expected: '59 Amber Cross, Practice Colony, Pune' [37:74 LOCATION] | detected: '59 Amber Cross, Practice Colony' [37:68 LOCATION]
- False alarm | item t066 | text: 'Billed party: Senthil Iyer\nDelivery: 59 Amber Cross, Practice Colony, Pune, 317283\nPAN XONCN2797D' | expected: '59 Amber Cross, Practice Colony, Pune' [37:74 LOCATION] | detected: '59 Amber Cross, Practice Colony' [37:68 LOCATION]
- False alarm | item t066 | text: 'Billed party: Senthil Iyer\nDelivery: 59 Amber Cross, Practice Colony, Pune, 317283\nPAN XONCN2797D' | expected: '59 Amber Cross, Practice Colony, Pune' [37:74 LOCATION] | detected: 'Pune' [70:74 LOCATION]
- Miss | item t074 | text: 'Billed party: Teresa Varghese\nDelivery: 46 Pine Street, Practice Colony, Indore, 926815\nPAN JNUCY2261G' | expected: '46 Pine Street, Practice Colony, Indore' [40:79 LOCATION] | detected: 'Indore' [73:79 LOCATION]
- False alarm | item t074 | text: 'Billed party: Teresa Varghese\nDelivery: 46 Pine Street, Practice Colony, Indore, 926815\nPAN JNUCY2261G' | expected: '46 Pine Street, Practice Colony, Indore' [40:79 LOCATION] | detected: 'Indore' [73:79 LOCATION]
- Miss | item t087 | text: 'Regards,\nKaur, Jasmeet\nOffice contact sample603086@example.com' | expected: 'Kaur, Jasmeet' [9:22 PERSON] | detected: 'Kaur' [9:13 PERSON]
- False alarm | item t087 | text: 'Regards,\nKaur, Jasmeet\nOffice contact sample603086@example.com' | expected: 'Kaur, Jasmeet' [9:22 PERSON] | detected: 'Kaur' [9:13 PERSON]
- False alarm | item t087 | text: 'Regards,\nKaur, Jasmeet\nOffice contact sample603086@example.com' | expected: 'Kaur, Jasmeet' [9:22 PERSON] | detected: 'Jasmeet' [15:22 PERSON]
- Miss | item t094 | text: "Campus map desk for F D'Souza: 41 Pine Street, Paper Mill Road, Surat, PIN 976137 | locker reference 221853" | expected: '41 Pine Street, Paper Mill Road, Surat' [31:69 LOCATION] | detected: 'Surat' [64:69 LOCATION]
- False alarm | item t094 | text: "Campus map desk for F D'Souza: 41 Pine Street, Paper Mill Road, Surat, PIN 976137 | locker reference 221853" | expected: '41 Pine Street, Paper Mill Road, Surat' [31:69 LOCATION] | detected: 'Surat' [64:69 LOCATION]
- Miss | item t095 | text: 'Regards,\nKamath, Chetan\nOffice contact sample603094@example.com' | expected: 'Kamath, Chetan' [9:23 PERSON] | detected: 'Kamath' [9:15 PERSON]
- False alarm | item t095 | text: 'Regards,\nKamath, Chetan\nOffice contact sample603094@example.com' | expected: 'Kamath, Chetan' [9:23 PERSON] | detected: 'Kamath' [9:15 PERSON]
- False alarm | item t095 | text: 'Regards,\nKamath, Chetan\nOffice contact sample603094@example.com' | expected: 'Kamath, Chetan' [9:23 PERSON] | detected: 'Chetan' [17:23 PERSON]

## other

- Miss | item t005 | text: 'Education row — Amrit; call +91 77307 20941 after 6pm; full record: Amrit Kaur' | expected: 'Amrit' [16:21 PERSON] | detected: none
- Miss | item t021 | text: 'Education row — Zain; call +91 60907 91073 after 6pm; full record: Zain Khan' | expected: 'Zain' [16:20 PERSON] | detected: none
- Miss | item t029 | text: 'From: Fiona Varghese\nneed the form today\nmail sample603028@example.com (nickname Fioy)' | expected: 'Fioy' [81:85 PERSON] | detected: none
- Miss | item t033 | text: 'group: Senthil Iyer and Rakesh Sinha are sharing PAN VABFG8868Y here — follow up with Senthil' | expected: 'Senthil' [86:93 PERSON] | detected: none
- Miss | item t045 | text: 'From: Simran Dhillon\nneed the form today\nmail sample603044@example.com (nickname Simry)' | expected: 'Simry' [81:86 PERSON] | detected: none
- False alarm | item t052 | text: 'Customer | M. P. Subramanian | Phone | 7242260964 | Total | 2400 | playlist title: ‘Cedar Cross’ (not an address)' | expected: none | detected: 'address' [105:112 LOCATION]
- Miss | item t053 | text: 'Ship to Yasmin at 63 Cedar Cross, Cedar Enclave, Mysuru, 467199; full record: Yasmin Pathan' | expected: 'Yasmin' [8:14 PERSON] | detected: none
- Miss | item t053 | text: 'Ship to Yasmin at 63 Cedar Cross, Cedar Enclave, Mysuru, 467199; full record: Yasmin Pathan' | expected: '63 Cedar Cross, Cedar Enclave, Mysuru' [18:55 LOCATION] | detected: none
- False alarm | item t060 | text: 'Customer | N. P. Murthy | Phone | 9750324784 | Total | 2400' | expected: none | detected: 'Customer' [0:8 PERSON]
- Miss | item t065 | text: 'Remit to payee603064@okhdfcbank; billing contact Yamini Gollapudi at sample603064@example.com — follow up with Yamini' | expected: 'Yamini' [111:117 PERSON] | detected: none
- Miss | item t069 | text: 'Ship to Aadhya at 46 Lotus Lane, Sample Nagar, Bengaluru, 411966; full record: Aadhya Daggubati' | expected: 'Aadhya' [8:14 PERSON] | detected: none
- Miss | item t069 | text: 'Ship to Aadhya at 46 Lotus Lane, Sample Nagar, Bengaluru, 411966; full record: Aadhya Daggubati' | expected: '46 Lotus Lane, Sample Nagar, Bengaluru' [18:56 LOCATION] | detected: none
- False alarm | item t070 | text: 'Payment footer: UPI payee603069@okhdfcbank / contact sample603069@example.com | playlist title: ‘River View’ (not an address)' | expected: none | detected: 'address' [117:124 LOCATION]
- Miss | item t077 | text: 'College circular — Aswathy Nair; contact +91 93058 10607 for details (nickname Aswaty)' | expected: 'Aswaty' [79:85 PERSON] | detected: none
- Miss | item t081 | text: 'Hostel update for Madhurima Sen — UPI payee603080@okhdfcbank for meal plan — follow up with Madhurima' | expected: 'Madhurima' [92:101 PERSON] | detected: none
