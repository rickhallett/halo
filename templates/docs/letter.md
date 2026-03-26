---
template: letter
variables:
  - name: recipient
    required: true
  - name: subject
    required: true
  - name: body
    required: true
  - name: date
    default: "{{ today }}"
  - name: sender
    default: "Kai"
---

{{ date }}

Dear {{ recipient }},

**{{ subject }}**

{{ body }}

Kind regards,
{{ sender }}
