---
template: test-letter
variables:
  - name: recipient
    required: true
  - name: subject
    required: true
  - name: body
    required: true
  - name: date
    default: "{{ today }}"
---

{{ date }}

Dear {{ recipient }},

{{ subject }}

{{ body }}

Regards
