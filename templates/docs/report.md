---
template: report
variables:
  - name: title
    required: true
  - name: author
    default: "Kai"
  - name: date
    default: "{{ today }}"
  - name: summary
    required: true
  - name: body
    required: true
  - name: conclusions
    default: ""
---

# {{ title }}

**Author:** {{ author }}
**Date:** {{ date }}

---

## Summary

{{ summary }}

---

## Detail

{{ body }}

{% if conclusions %}
---

## Conclusions

{{ conclusions }}
{% endif %}
