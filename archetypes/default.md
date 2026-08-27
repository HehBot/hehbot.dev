---
date: '{{ .Date }}'
draft: true
title: '{{ replace .File.ContentBaseName "-" " " | title }}'
slug: '{{ .File.ContentBaseName }}'
post_num: 1
---
