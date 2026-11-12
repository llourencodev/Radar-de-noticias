/* Radar Inteligente de Notícias — interface (JavaScript puro, sem build) */
(() => {
  "use strict";

  // ------------------------------------------------------------ ícones (SVG inline)
  const P = (d) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
  const ICONS = {
    home: P('<path d="M3 11l9-7 9 7"/><path d="M5 10v10h14V10"/>'),
    receipt: P('<path d="M6 3h12v18l-3-2-3 2-3-2-3 2z"/><path d="M9 8h6M9 12h6M9 16h3"/>'),
    scale: P('<path d="M12 3v18M5 21h14M6 7h12"/><path d="M6 7l-3 7a3 3 0 006 0zM18 7l-3 7a3 3 0 006 0z"/>'),
    sparkles: P('<path d="M12 3l1.8 4.7L18 9.5l-4.2 1.8L12 16l-1.8-4.7L6 9.5l4.2-1.8z"/><path d="M19 15l.8 2 2 .8-2 .8-.8 2-.8-2-2-.8 2-.8z"/>'),
    code: P('<path d="M8 6l-6 6 6 6M16 6l6 6-6 6M14 4l-4 16"/>'),
    cpu: P('<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/>'),
    briefcase: P('<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5a2 2 0 012-2h2a2 2 0 012 2v2M3 13h18"/>'),
    layers: P('<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/>'),
    radio: P('<circle cx="12" cy="12" r="2"/><path d="M16.2 7.8a6 6 0 010 8.4M7.8 16.2a6 6 0 010-8.4M19 5a10 10 0 010 14M5 19A10 10 0 015 5"/>'),
    search: P('<circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/>'),
    refresh: P('<path d="M20 11a8 8 0 10-2.3 5.7"/><path d="M20 4v7h-7"/>'),
    theme: P('<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>'),
    menu: P('<path d="M4 6h16M4 12h16M4 18h16"/>'),
    external: P('<path d="M14 4h6v6M20 4l-9 9"/><path d="M18 14v5a1 1 0 01-1 1H5a1 1 0 01-1-1V7a1 1 0 011-1h5"/>'),
    close: P('<path d="M6 6l12 12M18 6L6 18"/>'),
    box: P('<path d="M21 8l-9-5-9 5 9 5 9-5z"/><path d="M3 8v8l9 5 9-5V8M12 13v8"/>'),
    wrench: P('<path d="M14.7 6.3a4 4 0 00-5.4 5.2L3 17.8V21h3.2l6.3-6.3a4 4 0 005.2-5.4l-2.6 2.6-2.4-.4-.4-2.4z"/>'),
  };
  // logotipos de categorias (imagem embutida: funciona no servidor local e no GitHub Pages)
  const LOGOS = {
    "acbr-logo": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGAAAABgCAYAAADimHc4AAAj2ElEQVR42u19d3wc1bX/99w7ZXelVbcsS7blCrYMtrFNNWDZIeDQQomckEbJ+5mQl4T8HuFHSVmLhCQE8lJIHsEPAiQvBGRIQiCUgAETHIorLsJFLrIkW5ZldWl3Z+be8/tjZqWVLMANE+fp6DOflbSzM3fOuad9z7l3CR8eEZgx4umnw/T6ypu0VqOJyB3sRAFAMxggQ7CKUmnRz+q//vW3j+jusZjAokUMIgaA0f/1w1zrhltV4s67zlRJfkgXjxrBRSWasvKFIAlmQGsFuD2gPXVA8x7Iln1/jPzojmsTb7xg1J81vxOAP35mSl33yJn0IVHZhg3WsJNO0u8+9fIaNXbaSdjfCRsETQADEAOGn/ofa626TxopseLv8ycuuvnlVRevVKgkfWjMZ5H6zIQnfzeyPZE5xQhFnsekMhhthMSeVnTt2gtqagfFFYQLsKcAQWBbgPMzYBTnIjK+CCInDNXaBF6/4rfDP3Hut5rOOaF17150o6pKYsEC9c8pgIULTSxerIqu+uL11jU339X12PrMrOq9iAobSUEgAEJpsK8mUMKXQFQJtCc6ad81ZzkZJXEr0riisObGb+0DmICDnHEBY4ouu2yy9cO7c2Vd+/KuaAmSK2p0aGU9RXa0IBxXZFsmhJD+WCB6JwEDYNbwoNEDxd3ZBtxppWzMniBCBQLJPVvuxnN//PGexYubQQTwkSmC8WHwv/Sqq2Tt4sWue/U1V7BjRYftiassI0MKIRFiAsAgg0Bg/4f82W8SwYoaiP99q9R3XqG6k83TASwFgw9qqtx/v4kFC9zw3T871YoUvO10ZcNY3ezZLzxJGUkls8wwLLJhRAQECMz+/TGQh0JCQsKSJmV1A1i6ndpf2cQtZ45LGlfNvllemjFjtLZ+sOuB9a+BX1UgSsnvkEkcde7HYqIgGlWjzz67LBotyUtWN8LudCn1wCKYcRRwlEAQmkAgeAJgImQ0tEva2iJod/MTI88/P+dg7O3MhQtNXH+9W3Dnz+dkTZ75tjP6bFd//2kn+88rjRGeJQuMCCRLKAI02J+5zCD2zUC/g4GQAkzP/z1s2hhhZlLJ6t0huv1Rz/GKP+ZecdXS4XMyz55TXi4Rix22JTnqApiQl2euuusu7c6d/12nvmOGVb1bM0Ew+SznNNuXEgJTSvUBLQgRw0b76+tZTzszq/7FF1sOxuysevBBN/ebsfnh6bOWipYcT973vFHS4lqZVhgeGCpQImLqsxpE/Q4ODhDBEwTlz2wkBcNhjag2UOqGDPuBpW4Xj0jwt75TuWzZMi/gI/1TCMCdeilhyRLFN3y5M9ElOHdHmwpB9LLeH6UGQ/szMc0LE/xwyDQtWO82kBI5XHLnTys/YJxiZF2dVRTOLsuadcZjnlMg8PhyKm4DmQpIsgfBBKkBqRmG9u+jGRDaP1L2QxHgpSaD0AA0BAGCCCQkGIDBAkUdZOb84m8m5U4+d/hTS3+CykrvcKMieTSZPycWM3LG5OhkTvFl4XEzrlErduflvbtXhKVFREgzO/3UAAh8gICv/wIEcjT1lGQRJubP6Z5x0t148cVBQ9gJzz5r7bz66kTWz+7/jjfqlLPUI8t5xH7HMEn4M5gkBBME/IOIgvsE4yDyfSkF77EfGIAAQQxi8gUQfJaZYUqJSJxFc32dJ84+eXZWVqho5huvv1AL6I9UA3aOKTeWfexjXnjeORd7Dd2TrQ0N2gjZQhMdpIZyr4nI8ySwthYyf6yDm2/ufi+BW11dPOL22ELrzLkV8b9vo/z6TmFrCbCAwQKWomCWDTB35Js7RQz2PJg9SVAiCSbANcn3FTzQtzIIBFaAsCwUbNpv6I3NDuae9+VlhxkNHU0BUO015U6F1jI5crzdXdvKmQ3tsMgIwjs6MJThtCNdJZhgkAF7Vxu87a3W8Ht++SQWLjTB3O8CO8vLjeoFCxzrnLnndNV3FeWtaVBRaQkWIpjN/iuR8Gcx+dzXwvcF7V4cNZmet/nkfGfTmcXupilZzrZwwutxEhBaHzBM9N6eAMUo1DawbKNlFkxwT77y4tEfqQBm3n+/AYD//ssHF+o2fam9tdmLKDJI959EqYchZgjmXiuEtGcjAjQx8pMSzqZGOGecewUWL3YHRj215eXJ4ssqrvMc4zx3TYMXaWo3++Irn9E6lUEw/GiWGA4xGoZJdF0+VWd+dY5hXjTKQnmeaVdMskLfuMBoOWu02hfWYGJo7ouaSDOIGWAFYgXAQFajg/j6erP5ks8+1ZslfxQCaB81V4CIQxdfVCCSmZnWliYt7BCpIIjv04KUPBgEHZidQWJxBsIuYNe2cDhc6BbfcNPfQMSoqpIAsOqyywSIOP7ZiqlepKAob+NeHYXpx1rc5/AFBxk2MUAMJkaT7aDzM7OScmZYYPPSG3KszknZPbun5ES9SXbz6s+6V8+QreeMQ6vpQdgET2iA/NELzRCKQUojKUy42kLbrhZ0nX76lI8sEZu5cKG56qITk2Ou/MzV7sadN7sbRTK/ucuizEwkmWFwmgcI7GqPBShiZLi+3UeaoAB/5moAof1xJFfXmnTqabNwH4BhwwgAJkyYgBoAct75icSqNs5u6oImP5alAak+A9BEMJjRTi7Up890sjPbbe/R33+9/oFf/XrA42wevXvnO2rO2I376var6Mb9EqaNhNBgSXAl4AavbZkENX408maPh3rzH07nYWALR0cDFi4EmKE/e01Wt5kbNVbXIEtYRJxu4vsiIOW66C6Jgs6YiDY3AS2DOHwAOiIBZHUqJN6uhXdaeRxz5hhAOQBQzcSJDgCRW9daHN7TRTLpkTAMDOZmFPnRjsse2ktykzQqZCZFx831D/zqXjAbiMUEmCllPjLPu3AX71jnhsuncrNwuS3HxJ5RETRML8T+iyej/d/PQHvsAjf0jelu5unKNVc94Wa9+crwQOR8bDUgFhOrZs1yhw8fPgYan8Jel61d+yTbGRCKYQYP38cRP6lxx+YgPHsct771LmV7lJYIpIFUDIQ1UaSxg+MNrcUj5l2ybs88UTb8prsz9hJ1j/zUgi/xus1fwLaIZpCBINRMz/g4iO1NAB2kXX3aRDs70fP7LZfO/08ICRApAIzKytT4qJqoe1T52ZOTrlHTok5DtLRYhbND7ax7PF2/y+C/P/lQwTOx26vfhYMjxESPggkqF0ClNr77/Rkqr+TcyN92J7JchLxw4LT8tKf3bA1GMmJCjStE24n5pCcWILGxAxGSQIDNUGCCJBMkAxk9LhKb9sP45CeB2DeBaVP9i02enMehHIiWNleCbEqZsAF+UDAgFYNNycnCMEITC7cD0GXrPKv6JHIGi4fV/7vFESdP25GdHSXrrw/cV/fYQz9OP2HPUfKdRy6AKft4JmB2jCwtbktYMNZtFxEz5LO8F6PqMz8eGD3FOTCzLberfmsCJ4+JumtWMNkZpNNi6ZTpEiQQ6nEg3qmDd8bI/JJ5589t+ML5y/FFQA8fwQlN4J4EDDLSfEx/k2cAEJrBQkKFCI5qD0zvxkGCad+E7H784To8jnFpmiv6JwRHpx5gHKn5wYIFeufnPjfD3tdxh+hq0ZH2uElWJkizb3oGDFOBOT6hkPKi9I61ceUfVNmld8fl2yoL2uw3sF4TwsjUBuXu7tK7d7QUZlx17T0gmgkAyMrlJAhIOgABmjVoELfGIDBrsJAgKSATzkHlNWWxmNlaXGzk7t7tVRM5+BDoyJzwlEUEgL3/+R+dOOPcXGvVDidPhEmxHjTX0syAaTKNz0dnKBGX4ya+FiJHOONHqAQUSNCASRxoj5Swu5JkrG/S5hlz7aLrvnIuALDUBksJBkGxjy3xoPl18H8KgDh9cIhB9aJF7p7rr++prqx0yjZssLBypVlWVWUhFjtq4fuRaABhI3j45ZcXZv35tS/0ZIz3REOLYYoQHFa9fjCV9oMBzZo7ohaZYSSx7KW/nvHtW9ateXTpanXO5KmJ7ctUhjCkolTSFPjSAKcxlKCcmlbl7e+ZIsaO/SlisdOlp00SCtAKkrWf6aaZPPSGoOjNxkgA2vgA/gUlRyLC6Mq7vtJhqjXVJ530BgBUB4Kc8OyztvVWF1cvqnCPxBwZR2B+CJWkxW9+N9I1M2/E8xuSEZdsjzioMPlcpBTIxgyXGHtHhahgTJbu2J835sUlT30zozSvh7tyDJiGgqtBgtLYJ3q5GIKFyL4u1G1r5rzzL9yG06d44tcPCNt0oCyAtIaAgXRLzQAU/KyaBYNYQTBDGB/w2IsWUeGXvlTIM879vjNl+r+Ze5pqx6yt/02iox5i+XK4t920uObCCxv9c5kmbNli47nnUHPjjcljJ4DKSl+rszJLOnKK3ci6N0UGDChmyDS0XwAwXT8S8UyikGnC6+SwN3nel424A+VGYW9thG0Zkl0XNMiQCAAJASseF9aGJp0oHX9a/u2Vl6iGhtZQ4VSdyM5kD/sgWATxVl/VQaSgbhKQroLZ6cJWGdLPqKe81+zXklnxiu3/1vJWQ2e4IVnqqpZK5ESROfPjsJ97a14Wq7Xe6y8btUT/twZIHlsNCFR0VOyuYjdu3iM3N4toXAspCDoNiwH3mRMAsBRh1KZ2uA1vIFtI11TEYG3IpCOMpAZIBDDCgekkE2BJU+TVtDrtOqNULfjMPOPaz1dh8tlC52daQWWTDhBcrwAI0tFs9whkiqwuLFigsIHlYFHQsGHDMkPf+8n39LmfdsN/XpFRmLA0Ld/liewMipfkcOcJw+bEh9tzMudeibFf+D+TPMNpildVOc3fuuka9MtCPqyifCCAMuainuV1e3p+86YzfEebFVL+jEvvYfBjcAFX+kwUnoJiDQLDUoAjAc8UECQguR/bBhkqoxOO2vv500V4kr0e5VOuCFU33hZ/c/+XCu571c2UtukaAZ7f7zoMSUC3cnTj7PFKnjOsQe34x815Iwr/Ur1xmEblXC+9oWDExQtN2dLQjfgInfHbN8QwIwLDYWhmdLOHTik8LyfCXkkO3BOHm87EPFCBRvM5k+hQW1YOTwOIuAywOr79w1u9OVfr8Oa90jYzAK0PYJ0GoGXgCAEoQ0AL4Zf/mKHhw5WkPmhO+Ama7bGMrNzpmiUTpyZv+fbczsnDV6POu44zQszx9/60YsCCFKF1tU7XxdPHyPPmF1dPmeCA2cSUqj5NWLDANTz7a/jiNzj+38tRJCwkwDAFoIWEJIk8DYNak3D3N6BrY71qPLGA7RvP6zmmTjjx4othNxn+mrdiK/LIlBqcVlHqbzo4na9MIJ3Kd/xMWTAdlCpqACFpIrRpj26ePwXmbd8NJX/9iLRPnEOtw8Mwt3XANKz+90sTqhQSWV2uzX9aqcS1s79det9Dl2iiq+uA3akzR9z0rQ3u1TeMF3/aRIW1HUTCgNbcO2HA/jjYIJiwkUWQjRk2ujM845gKwF29fqp1wbUCDz6lTSmhwUHMQoPbOe4TBKW9QwdhC/sQUg0DhIyksjve3eOKAueH5rNP/cSeOq+qY9qYimjtes8ADA0N4qAAMyAbCAmTkmtrZctD3rDwWbPOCz+/vrrU7XQ1NAw7CxQ3C9r+9C6y3tiJCKzeGNoNyqaUFl8bILRLDS6Jwt60VnYdSwF4VvRlqmlG9t5uYUgbYO5tcHpPNqZpweG4n1TnhGVZsNY3aOeccZnmLTe9q+reNYxTJlP32zs51NgJIcX7XJ0R1QaMNXu4bUczNZXkZFNeJjQxqLMZWbt7eER9O4WEn+Ah6NRg+AX8dKSDPY2OQhvR6aNY/PX+7+xPgzI+1Ez45FtvzdWTphvtS1ciCyZM5TtUyf1ToNSPJg3tKVDSATsO2PVAjko7PLDrQrsuoJUPyqWaptICChFcVRsGzF3NpPe5rGfPzk3++udOZnZCt04tFJ3CTfEt6P3BgcCcJkSVpJImFyesacK4pdsx9oUdmPDmXoyoT1CUTRiKejsoMDC0IUCSQJdOQk0t1l44Ttf+6p6fHAsTRKioEE1sPUucg+wdcQgRtMTwgSYDxPCIETc0nNywFlKSY5CfqnFvtSDQas2stI50JkVmQpHfMJXKJ6gXmWDygbUMFlbrWxsTqihxn3n5ReWJmuqYcf6MO/bX7lfm1mYjImw/CdRB6yPgh7lpuiek6BWsmR6Qsui1M4IIVnBfCL+U6gmCUIz6QoPteeMFlj2+o7JymsBhdEUcmh0IQqxhL7we19UyNPKJaoRFUIVi6rXxOsUtYnSRQvP4bODKGdBOF5TnQQuCFqmH1CANv90jLx+0Zg8KXtyC3G5fC/rSOfQ+HxNDsUJjFE7y9k/KSKjlp7WnnnRz6bK1T3W2ZV5k/PfLVNLGIkNLsAY82deCcrC2jnvNZp/wiQFPEjyh0MZJbvnaeWSGm9c1X3LOtMPtETUOVVilX1w4V4aHoX39Owi7AKTumzSpB0x1QIPQZQHW7EnghrW14h8vvyYSbrsWJEDCJrBirV2Q1Ow5WZh+SkH3zPNnxqv3FWVtaGTDsokHezAmSGkiur/D0mvqXYzo+OaoL33tNe8T5d/NeOLZS9srZunGR9/ySjrZMKThmy2knCgd1JMO6GAK8CR/LnSyo9ovmZbMmGiridNmn77sU5+SqKrSh4MJHbwAXnlFgsjTd937cqKmHeHdnQxJpP2uJn+GkECqCYIFA0rDybWVnDFK2v/zzHXbH77/5fe9R9UjGLGr43fxCa2f79nYqDKDKldfrNTXYQcNZJlh7FuxScW/MEPkXfXprm0P3vvOyGf/eFf+pz5/S9fV54q9f3g7mdvYY1u27belsOgt2PeBfamWSU4znxS0z3PvbUkSkqzQynGv59LpRnZ5aUT96p7Ypr88JtHYmDxo7TrSKMi75PJafnhtaWEXA0YQKVCffU0FOSQI8ByIgly0y4TTdc+3V0xwmmyrMY9RNkiiNGqUrbqLncS+ejtZGNaJ3Agyuv2CDKVltKmEjAFISyCjodXo3q+RGGZ+Kv/fb95c/8u7by1wVU/W/Cuucv593qTWFzcnxVs1FHK1FTXDMIMuORYicPRB60qqaTK4lakAwQRXMLTnob2nW7eeWJBwP10eMXITG9Qrz7zU3tT2i/ampu5DhR+OSABuOAu6sS3p7u9gxzDIH7ACkeytBJraF0A7J+GUnuCF312TEXrsnsyae+99z0peaewhUVt5YbLou3cOi55VIbozzZ5QbaNpSgsIGtnB6EM7WUNZDM9pp+SWhh7jxBO/IkqGPV0WizVXV1begef+8kzWU3+9ki4cc3vH2ePRvmZ7sm19I4XrWjmacI2QFZJkSgACgvrMJpPvj1xHIe54XmuWVFw2Aslp02xZlh/JKKSliddfu2XXzV9ZBSGOeLXMIQuAt1WX6us/juZL45Ccirf9Nm8IQAlfAFoxWkwXxvRiO+MPv640lv+ptfl9BltbneFi5UpT33nPD+KXVEzlW67I69y2F1IaYEorqPTWGDSYFLpVEjy52Ers3bLYHlm0ujoUUqWxWKi2snJ18ymTVpf88je7zDPPHGNHC271zpuIni6Jzvr94PrmpGztJNHtseEqwFPwBKBsCWSGwPnZMMYU2bo4aoiogtnasMLKTvwmcfHlLzTv2rJjZFVVuH7BgsThzvxDj4IC5hX8ruoi/clLQxI2ZG+Rzutt81WpVweIW9BWe4toHzX8yYO8hwSRCm+pOyNz9MiR0oFOH6OS/m1SsJFUHuJhQyGeNKIbVv+1/qyz4ojFBCorNSoq5MxbqsSqWf66tNE/+68r5WWXwMkrQrLqqa+KaHa5EiZkJAtk2oAGFBiskqBkD0RbMyTUX6zPXvmwXr3KVD++e+3uPz++BUTA448fleVJh4+GHt59Dm6mVFRILFlyeA83iIbNvP9+c9UNN7jpZcgTw/nF3n984wQ1dqyWw4cLLzMTMAzA84CuLqCxHua6dSzu/enGLUBz77VWrjRXzZzpHa2C/OEJIPaKgfLyfv+aGV1F47ZvH+RaG4EyoKK6UlVsPHhVvf6S+2VrKJf8+p9P28eN41WdMwdc49VUawxQDvU+jCHEXpF+T1c5MJe8Q4j+fDP96qsalZX6w5iZ//uImbBgiUDF+5yzZAmwpEofaqfbsRSAb1ayL8qt/GT1fdec3XyBiHhKa1cSEaTov4BQB9FRL0SdKtT3Zs59eZxggJMC+7olGlptbNkTxvq6jJcefmbrguC++khCv38mOmwBcAyCKqFfvSVyypTT5eqC0xnI1gjA/rScKUjN2AA8BoyEH3yl2oCCRA6kAUP5Dl2zXypzDXBCwG1yEG/QqN2V4f3mlfy3dleH5y2prvCYK5no+BbCEXfG5ZguMrMYKFSOEo6VEikNLNDC8WUhAMAFsdsPWmAQlNB+SZMBCgUrGTXByidYEySmtDjiexP3zF6+MvL8Jft/fQmAnlgMorIS+ngVgDg6JjUoBAeAVaoNZ+DST6I+UKu/HvqdfjJtHVevpREK2nLBGQ7ESE9ETzXd+R935k4a1fPEXQtys77/PehY7ENYbns8CaAfaE7vc877HtQLP/dehAYUcoQHzk6YOIGcqafo+SeeIB+ZXz6xZAr6L0H43yeAoxOaYJBFY747oaBjhQCPXLhRx7Knez0zp7ufnDkq8eUFlXB/MX+C9b/SBxy2yRpUAOl5FB0gjD6LlQSyhBw1k/VXutvr73gE/PXravjG5wfXva8dhHDufb7GAcBz5swxrpjaICdOqMEEADUAttYANVsnoDFa4y1ZAvXPMV8Du7v22+YpPS+FmT0j6Smw0v6htQ82DnZoBism9jSxp8GeBjsMdrX/nn+eYGYZvPb/rFZgh4XHbeStezD6/GfPO/FkroKMDdI0y3xwa6GZQc/+fIL9vuaCgGd/PsGOHUXLYRxTCxO8cg8BLmlpaTe1EYoEQUtpwIBkUj4GP2B9AQJcVAMgzRIkEpHM0AWjCrqfpgVYH6tYYvnhln9qLAYiInX5+ZN/bJBSmmkQYbBnS9MgWn8rQMnxU86a+5nTGj5x1ph2jIi6SLrg9bvD+Mf2HHr41dIHLrxx6RYhgNh3jk70dewE0Lt2lKB3SuzbbIqmrpBtmgBYID+qkFPYDVkqYRQQmLz3SEJ9M0UAIEyKhD01ZbjbCQDFudX9PlBZCf3SD7KfyMrZcyUEg/UgLY/MMEjgjstCk9fuHLEvL3PDx8eW8cjicQJWxAZcgUn7FM7YsQ9f/Vj9nFU7R1dXPjX8h5WVK7ZUVFTIJYeLW31kPoDA3C1p7arQ1ne2h26ORNhkllSU5ej8Eeb1p83Hx7PyWTEJSRiwyDhVpOe+mMfThLhnDBIBEX99wbibzj1115XmqW4yiHB5EM0keGDU08XDR3Yis8wBhjkObAMwJABCzgkucmYooMU4beK25tPy8xPTl7877otZjy7ZeKR5iHE0Z3hfTzS/X9zFkILaPdF02+N7nkp/6z+/WnTq9O7ujwOeAki+13VSK4ylx9zaEpZv77QjwD6swkwAq3pVzXMnfExbrqeiwq/qiHTj3V9mbT3Kyy1OsM4hySQsggIpBRbsQ+wZEsIO66xQZ3fp1uj0F96ksT8F1ldVH9l+G0dVA4gOovFAgwQYttAFKDhnxnnj90cSyhg5rTR59azRDWdmZ3lasTQJ3qCMTzHOJMtBN9k5yeafNHdN+sPK+2HOun6VN2BSJDxFhqn94qN8jwicwYgWkqGEhhAcrLTs68QgZjAUJLkemuwMGe/4BtHIl5ghiXCcmSAwuZkuzpnrTKib8+ZSApPWZFoWRXKKFIxRVrBArG+ZDPepju+C2YBMSu3WG7Rrr1P31LJ32j5XDusA1WOmfvuEHLAvQl9gYJhp+0EMttKbBNDj6rpNWeKdzWbt4mdW9Vy16Mj5Zxx79gPWGIGC0UJCIsefZAqAC5jEWjhEqe0LBuxroyGh2YNkE9irjOXLI/ivN4tMYDNtrC4D0gsIBxWSDUzkeVABMQEmKIl2aXfFO//jDTXtr7yyyaRZcI9LAXDITemtX+rV/nJpFkwc7O5Bg2XJrCA9A3Kf5257w3JXVcs7ljy/+T+rYmXmgsrqQ1zFyAN+S19f1pcMsmY/AehRaKgO09K1Gc7ixavchTNhHpdQhIBf1w0OkkGvFPsBh79JEg2GK2lAu+Ddyu1cIY2Na0J/+eaDl/6IGbwR1d57u5yDDM0goEFwwVBEYBKaiRkkILTJ6BCo3hBqffmd3E5m0NO75/BxKYD3zRE+4JGkABBlMzzO8caX8Wdu++KLv19QPizjjsojR0RJGRBaQkLA6DCUaCUhOjUJRZ5Usie+LdPet1//7E9LN/32uV/Aqqxc5h2NRzc+UsZzGv9psODwwP/JHAYitjklvyvxHznJiqrn8xJ1yWm3tbR0NwM+nnN4U9EDE0PuF+h4k+TuerG9W4jMorFmYUkJjNVv222PvTVsVyx2svHWH6GAZccxGhq0o3GwPVk6OMf83izsxUrNJNQwDhXMcLrnz3a+cMHk5rn33luTjMXKzMMdEJMGuSHEN7B+5vXoo5O/edbl1/1q6tW/fSL3yXUvGU92t/ANT79c/fAlxV1UuezozP6PQAOCmFILwAVTSASOU/UOR0GYpJUguANW06T5BQYEefDybXvcWfuTV3WE5u1sKX190ZTqOgCichDTTwN9b5rZIxCgJaiDULvZdj53V/PnpHgZ69Zh3bp1eP724NQ5c+YYs65f5h5Njhx7E8QEr05A79XE0rb97j4NkoAZFZAhDyqPNMIk+oeiaXt/pP4OJw3kGF64IPPaE7K9l2kBfv9KDDIdGhAIivyBdg2aKPpd8nD2JbGmNhfP/rzHfuh1eE1Nc+iKqQ3yExNq0NACNbfy6M38j0gA/sZtei/orZdCuxIu/dSSWnqKlAk2CqMJdy/Ct516njc8cqJSHNIHwBG9C1AJ/srKLBMjxvV4Xz23c9u3fnvo9t+Pg/2ruj0KW/bactEPUwuvl2HZMng3/ksVZAhMUtKezoz6T9/V9LOBb8c+XfDclPF1SyJjjZMp5ARl/D57Iai/JBQc08xJ4rebR/xg1skFXypftH4HLzq4ZQC9VjFoRRcusL/LbDzWYfkxTwSYBez3uHNNwpjbo43hwb6RdBAIoIStvVDIKs+PouRQ21R60y9NIIfQE5ePHEt2HHsN0Cw0XNh2YtptV5e+FZGaFINNS4lxeUk1pmj3qUUTlYCh2O/1fB9ZsoBmA4BiEMPmI9i/2SOQkpBCv/qvLQAAxjDCuec7GbO5+TTiYF9JgxAKGTCyFVDgMeyD2H+TGEIJD0lpJ53EkrUNZ68nWp/qYqdD04Kgk4yo519bAATIkR4iJQIQXt/W2aQAbQBaEgtBxHoQYGygQ9YgycrtDBsTc9se3bXr0dZXYjDmVqZh2YfoliXI+hcWQLCcw/CZ58NcFAQhBJAHSC/gGx24jp7Tt0MM1nclkrxrWxgrt0YYaMKrRzg8fYg73x5nTpiDHWg1CDqAv4JdpXmwVjodwGmp/lL0bj6hAbCKMOose8U7VuKVrQVJAHRkEvgIzPFHib314pXvgwMFQEEAF/TtAw1psuzhZGut7MozOq57etne5/2qGNzjSQDHTU9latcBjwClwixcu1vtlKG//UP+6IJY/OmHYggNZD7RP3+74lHRAJ2ql3B/vObooRcUwEgCwiNXtkpT11Dm75/O3Fe1YlhDLLbO2PnqHG8gQklEJnPqewDS0LyB40t9pYw+DgUQluAMCw6k4Qh46I8xH6pBGlgY8L/yh6ABxRDdJNBimXvedNpXbMh57sFl+VWvvbnuTyUTZpqLlx0IkmnmiGWwI0wZLAV571lBNiFkKpBgcVwJYGVjnpXdAmv4vm4LYROD7tjU7/f3Q/wDHnka8IRvb1wB7lBobLRQvUFgjJX476Wb8pZf/4vGR4RoQkVFhVy8eIk7aJomxj6WjIfLzf0cPCkf4Hd65ZwU6GiLwKJk3UfnDw/9s/yVC8uKTpnStXDeqU3KNQzpCQ8QqS/H6ZtM/t/6g92OBjw3EEBCA55GZ7fBb+7Iode3ZO1/8sXNvwIYD8VKQ89Wn+Z+UGfa83flfXfMmC7W0iCI/pt+9KOkRvWGHFTc2XjHcb/u6UN1xith3r/w4Arix8PCjSOOEhigJbEys2xKNQbbA+KwaJDukuqNZXhpT5gXL151SGHmhir4mW3ZQdxzYxlOOuTuiiEaoiEaoiEaoiEaoiEaoiEaoiEaoiEaoiEaoiEaoiEaoiEaoiEaoiF6b/r/ZvT4aeV+ctcAAAAASUVORK5CYII=",
  };
  Object.entries(LOGOS).forEach(([k, src]) => { ICONS[k] = `<img src="${src}" alt="" class="logo">`; });
  const icon = (n) => `<span class="ico">${ICONS[n] || ""}</span>`;
  const hydrateIcons = (root = document) => root.querySelectorAll("[data-icon]").forEach((el) => { el.innerHTML = ICONS[el.dataset.icon] || ""; });

  // ------------------------------------------------------------ utilidades
  const $ = (s, r = document) => r.querySelector(s);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const safeUrl = (u) => (/^https?:\/\//i.test(u || "") ? u : "#");
  const store = {
    get(k, d) { try { const v = localStorage.getItem(k); return v === null ? d : v; } catch { return d; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch { /* sem armazenamento */ } },
  };
  const STATIC = !!window.RADAR_API; // versão publicada (GitHub Pages): dados em JSON, sem servidor
  async function api(path, opts = {}) {
    if (STATIC) return window.RADAR_API(path, opts);
    const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.detail || `Erro ${r.status}`);
    return data;
  }
  function toast(msg) {
    const t = $("#toast"); t.textContent = msg; t.classList.add("show");
    clearTimeout(toast._t); toast._t = setTimeout(() => t.classList.remove("show"), 3500);
  }

  // datas: published_at é UTC ISO (com hora) ou AAAA-MM-DD (apenas dia, informado pela fonte)
  const fmtDT = new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
  const fmtD = new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "2-digit", year: "numeric" });
  function pubDate(a) {
    if (!a.published_at || !a.date_confirmed) return `<span class="nodate" title="A fonte não informou a data de publicação">Data não confirmada</span>`;
    if (a.date_precision === "date" || a.published_at.length === 10) {
      const [y, m, d] = a.published_at.slice(0, 10).split("-");
      return `<time title="Data de publicação (a fonte informa apenas o dia)">${d}/${m}/${y}</time>`;
    }
    const dt = new Date(a.published_at);
    return `<time datetime="${esc(a.published_at)}" title="Data de publicação">${fmtDT.format(dt)}</time> <span>· ${rel(dt)}</span>`;
  }
  function rel(dt) {
    const s = (Date.now() - dt.getTime()) / 1000;
    if (s < 60) return "agora";
    if (s < 3600) return `há ${Math.floor(s / 60)} min`;
    if (s < 86400) return `há ${Math.floor(s / 3600)} h`;
    const d = Math.floor(s / 86400);
    return d === 1 ? "ontem" : `há ${d} dias`;
  }
  const fmtLocal = (iso) => (iso ? fmtDT.format(new Date(iso)) : "—");

  // ------------------------------------------------------------ estado
  const S = { meta: null, cats: {}, status: null, route: null };
  const STAGES = {
    nao_determinado: "Estágio não determinado", projeto_de_lei: "Projeto de lei", consulta_publica: "Consulta pública",
    norma_aprovada: "Norma aprovada", norma_publicada: "Norma publicada", norma_em_vigor: "Norma em vigor",
  };

  // marcação "Notas técnicas / ERP" (mudanças que exigem ajuste em sistemas)
  const ERP = { name: "Notas técnicas e ajustes em ERP", short: "Notas técnicas / ERP", color: "#c2410c" };
  const ERP_DOCS = ["NF-e", "NFC-e", "NFS-e", "CT-e", "MDF-e", "NF3e/NFCom", "BP-e/GNRE", "SPED/EFD", "EFD-Reinf", "eSocial", "DCTFWeb", "IBS/CBS", "Documentos fiscais"];
  const erpBadge = (a) => (a.erp_impact ? `<span class="badge erp" title="${esc(a.erp_reason || "Pode exigir ajuste em sistemas")} — classificação automática">Ajuste em ERP${(a.erp_docs || []).length ? ` · ${esc(a.erp_docs.join(", "))}` : ""}</span>` : "");

  // ------------------------------------------------------------ componentes
  function catOf(slug) { return S.cats[slug] || { name: slug, color: "#64748b", icon: "layers" }; }

  function noImage(a, mini = false) {
    const c = catOf(a.primary_category);
    if (LOGOS[c.icon]) {
      // categoria com logotipo (ex.: ACBr): o logo ocupa o lugar da imagem que a fonte não fornece
      return `<div class="noimg logo-ph" style="--c:${c.color}"><img class="brand-logo" src="${LOGOS[c.icon]}" alt="${esc(c.name)}">${mini ? "" : `<span class="outlet">${esc(a.outlet)}</span>`}</div>`;
    }
    return `<div class="noimg" style="--c:${c.color}">${icon(c.icon)}${mini ? "" : `<span class="outlet">${esc(a.outlet)}</span><span class="note">Sem imagem da fonte</span>`}</div>`;
  }
  function imageBlock(a, mini = false) {
    if (!a.image_url) return noImage(a, mini);
    return `<img src="${esc(safeUrl(a.image_url))}" alt="" loading="lazy" referrerpolicy="no-referrer" data-fallback="1">`;
  }
  function badges(a, full = false) {
    const out = [];
    (a.categories.length ? a.categories : [a.primary_category]).forEach((slug, i) => {
      if (!full && i > 1) return;
      const c = catOf(slug);
      out.push(`<span class="badge cat" style="--c:${c.color}">${esc(c.name)}</span>`);
    });
    if (a.erp_impact) out.push(erpBadge(a));
    if (a.doc_type === "oficial" || (a.official && !a.doc_type)) out.push(`<span class="badge official" title="Publicado por órgão oficial ou pelo próprio fabricante">Publicação oficial</span>`);
    else if (a.doc_type === "jornalistica") out.push(`<span class="badge journal">Notícia jornalística</span>`);
    if (a.legal_stage) out.push(`<span class="badge stage ${esc(a.legal_stage)}" title="Classificação automática do estágio da norma">${esc(STAGES[a.legal_stage] || a.legal_stage)}</span>`);
    if (a.is_update) out.push(`<span class="badge update">Atualização</span>`);
    if (a.nature === "opiniao") out.push(`<span class="badge opinion">Opinião</span>`);
    if (a.via_aggregator) out.push(`<span class="badge warn" title="O endereço original não pôde ser confirmado; o link abre pelo Google Notícias">via Google Notícias</span>`);
    if (a.group_sources > 1) out.push(`<span class="badge" title="A mesma notícia foi publicada por outras fontes">${a.group_sources} fontes</span>`);
    return `<div class="badges">${out.join("")}</div>`;
  }
  function providerLabel(a) {
    if (a.provider && a.provider !== "regras") return `Resumo gerado por IA (${esc(a.provider)})`;
    return a.summary_lang === "en" ? "Trecho original (inglês)" : "Resumo automático com trechos da fonte";
  }
  function card(a) {
    const c = catOf(a.primary_category);
    return `<article class="card" style="--c:${c.color}">
      <div class="thumb">${imageBlock(a)}</div>
      <div class="card-body">
        ${badges(a)}
        <h3><a href="${esc(safeUrl(a.url))}" target="_blank" rel="noopener noreferrer">${esc(a.title)}</a></h3>
        <div class="meta"><span class="outlet">${esc(a.outlet)}</span>${pubDate(a)}</div>
        ${a.summary ? `<p class="summary">${esc(a.summary)}</p>` : ""}
      </div>
      <div class="card-foot">
        <button class="linkbtn" data-open="${a.id}">Detalhes e impactos</button>
        <a href="${esc(safeUrl(a.url))}" target="_blank" rel="noopener noreferrer">Abrir original ${icon("external")}</a>
      </div>
    </article>`;
  }
  function listItem(a) {
    return `<div class="list-item">
      <div class="mini" style="--c:${catOf(a.primary_category).color}">${imageBlock(a, true)}</div>
      <div>
        <h4><a href="${esc(safeUrl(a.url))}" target="_blank" rel="noopener noreferrer">${esc(a.title)}</a></h4>
        <div class="meta"><span class="outlet">${esc(a.outlet)}</span>${pubDate(a)}</div>
        <div style="margin-top:6px">${badges(a)}</div>
        <button class="linkbtn" data-open="${a.id}" style="margin-top:6px">Detalhes</button>
      </div>
    </div>`;
  }
  function fixImages(root) {
    root.querySelectorAll("img[data-fallback]").forEach((img) => {
      img.addEventListener("error", () => {
        const host = img.closest(".thumb, .mini, .hero");
        const id = img.closest("[data-aid]")?.dataset.aid;
        img.remove();
        if (host) host.insertAdjacentHTML("beforeend", `<div class="noimg" style="--c:var(--text-3)">${icon("layers")}<span class="note">Imagem da fonte indisponível</span></div>`);
      }, { once: true });
    });
  }

  // ------------------------------------------------------------ navegação
  function renderNav() {
    const counts = (S.dash && S.dash.by_category) || {};
    const items = [`<a class="nav-item" href="#/" data-route="dashboard">${icon("home")}<span>Painel</span></a>`, `<div class="nav-label">Categorias</div>`];
    S.meta.categories.forEach((c) => {
      items.push(`<a class="nav-item" href="#/c/${c.slug}" data-route="c/${c.slug}" style="--c:${c.color}">${icon(c.icon)}<span>${esc(c.name)}</span><span class="count">${counts[c.slug] ?? ""}</span></a>`);
    });
    items.push(`<div class="nav-label">Destaques</div>`);
    items.push(`<a class="nav-item" href="#/erp" data-route="erp" style="--c:${ERP.color}">${icon("wrench")}<span>${ERP.short}</span><span class="count">${S.dash && S.dash.erp_total != null ? S.dash.erp_total : ""}</span></a>`);
    items.push(`<a class="nav-item" href="#/todas" data-route="todas">${icon("layers")}<span>Todas as notícias</span><span class="count">${S.dash ? S.dash.total : ""}</span></a>`);
    $("#nav").innerHTML = items.join("");
    markActive();
  }
  function markActive() {
    const r = (location.hash.replace(/^#\/?/, "").split("?")[0]) || "dashboard";
    document.querySelectorAll(".nav-item").forEach((a) => a.classList.toggle("active", a.dataset.route === r));
  }
  function parseHash() {
    const h = location.hash.replace(/^#\/?/, "");
    const [path, qs] = h.split("?");
    return { path: path || "dashboard", params: new URLSearchParams(qs || "") };
  }
  async function router() {
    const { path, params } = parseHash();
    closeMenu();
    markActive();
    const view = $("#view");
    view.innerHTML = `<div class="grid"><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div></div>`;
    try {
      if (path === "dashboard") await viewDashboard(view);
      else if (path.startsWith("c/")) await viewList(view, path.slice(2), params);
      else if (path === "todas") await viewList(view, "todas", params);
      else if (path === "erp") await viewList(view, "erp", params);
      else if (path === "fontes") await viewSources(view);
      else await viewDashboard(view);
    } catch (e) {
      view.innerHTML = `<div class="empty">Não foi possível carregar: ${esc(e.message)}</div>`;
    }
    view.focus({ preventScroll: true });
    window.scrollTo(0, 0);
  }

  // ------------------------------------------------------------ painel
  async function viewDashboard(view) {
    const d = await api("/api/dashboard");
    S.dash = d; renderNav();
    const st = d.status;
    const last = st.last_finished;
    const healthTxt = { ok: "Coleta normal", parcial: "Algumas fontes com falha", falhas: "Muitas fontes com falha", parado: "Agendador parado" }[st.health];
    const section = (title, items, link, mode = "grid") => `
      <section class="section"><div class="section-head"><h2>${title}</h2>${link ? `<a href="${link}">Ver tudo →</a>` : ""}</div>
      ${items.length ? (mode === "list" ? `<div class="list">${items.map(listItem).join("")}</div>` : `<div class="grid ${mode === "lead" ? "lead" : ""}">${items.map(card).join("")}</div>`) : `<div class="empty">Nenhuma notícia ainda. A primeira coleta pode levar alguns minutos.</div>`}
      </section>`;
    view.innerHTML = `
      <div class="page-head"><div><div class="eyebrow">${new Intl.DateTimeFormat("pt-BR", { dateStyle: "full" }).format(new Date())}</div><h1>Painel de inteligência</h1>
      <p>Notícias reais coletadas de fontes oficiais, imprensa e buscadores, organizadas por assunto.</p></div></div>
      <div class="kpis">
        <div class="kpi"><div class="label">Notícias coletadas</div><div class="value">${d.total.toLocaleString("pt-BR")}</div><div class="sub">sem contar duplicadas</div></div>
        <div class="kpi"><div class="label">Publicadas hoje</div><div class="value">${d.today.toLocaleString("pt-BR")}</div><div class="sub">pela data de publicação da fonte</div></div>
        <div class="kpi"><div class="label">Última atualização</div><div class="value small">${last ? fmtLocal(last.finished_at) : "—"}</div><div class="sub">${last ? `${last.new_items} novas · a cada ${st.interval_min} min` : "aguardando a primeira coleta"}</div></div>
        <div class="kpi"><div class="label">Situação da coleta</div><div class="value small"><span class="dot ${st.running ? "running" : st.health}" style="display:inline-block;margin-right:8px"></span>${st.running ? "Coletando…" : healthTxt}</div><div class="sub">${d.sources_total} fontes ativas · ${d.sources_failing} com falha</div></div>
      </div>
      ${section("Mais relevantes", d.top, "#/todas?sort=relevance", "lead")}
      ${section("Oficiais em destaque", d.official, "#/todas?official=1")}
      ${d.erp ? section("Notas técnicas e ajustes em ERP", d.erp, "#/erp") : ""}
      <div class="cols">
        <div>${section("Últimas fiscais", d.fiscal, "#/c/fiscal", "list")}</div>
        <div>${section("Novidades de IA", d.ia, "#/c/ia", "list")}</div>
        <div>${section("Programação", d.programacao, "#/c/programacao", "list")}</div>
      </div>`;
    fixImages(view);
  }

  // ------------------------------------------------------------ listas (abas)
  // períodos pela data de publicação: [valor na URL, rótulo, dica]
  const PERIODS = [
    ["1h", "Última hora", "Publicadas nos últimos 60 minutos"],
    ["24h", "24 horas", "Publicadas nas últimas 24 horas"],
    ["1", "Hoje", "Publicadas hoje (desde 00:00)"],
    ["7", "7 dias", "Publicadas nos últimos 7 dias"],
    ["30", "30 dias", "Publicadas nos últimos 30 dias"],
    ["90", "90 dias", "Publicadas nos últimos 90 dias"],
    ["365", "1 ano", "Publicadas nos últimos 12 meses"],
    ["", "Tudo", "Qualquer data"],
    ["custom", "Intervalo…", "Escolher as datas de início e fim"],
  ];
  // início do período em ISO UTC sem milissegundos (mesmo formato salvo no banco)
  function periodStart(period) {
    const isoZ = (d) => d.toISOString().replace(/\.\d+Z$/, "Z");
    const m = /^(\d+)h$/.exec(period || "");
    if (m) return isoZ(new Date(Date.now() - Number(m[1]) * 3600e3));
    const days = Number(period);
    if (!days) return null;
    const d = new Date(); d.setHours(0, 0, 0, 0); d.setDate(d.getDate() - (days - 1));
    return isoZ(d);
  }

  const EXAMPLES = ["Nova Nota Técnica da NF-e", "Mudanças no IBS e CBS", "Atualização do C#", "Novo modelo da Anthropic", "Alterações no ICMS de Minas Gerais"];

  async function viewList(view, cat, params) {
    const isErp = cat === "erp";
    const isAll = cat === "todas" || isErp;
    const base = cat === "todas" ? "todas" : isErp ? "erp" : "c/" + cat;
    const c = isErp ? ERP : isAll ? { name: "Todas as notícias", color: "#0b5cad" } : catOf(cat);
    const fiscal = cat === "fiscal" || cat === "reforma" || isErp;
    const f = Object.fromEntries(params.entries());
    const q = f.q || "";
    $("#searchInput").value = q;
    const opt = (v, label, cur) => `<option value="${esc(v)}" ${String(cur ?? "") === String(v) ? "selected" : ""}>${esc(label)}</option>`;
    const outlets = S.meta.outlets.map((o) => opt(o.outlet, `${o.outlet} (${o.n})`, f.source)).join("");
    view.innerHTML = `
      <div class="page-head"><div><div class="eyebrow" style="color:${c.color}">${isErp ? "Impacto em sistemas" : isAll ? "Visão geral" : "Categoria"}</div><h1>${esc(c.name)}</h1>
      ${cat === "reforma" ? "<p>Publicações oficiais têm prioridade. O estágio de cada norma é classificado de forma conservadora: uma proposta nunca aparece como norma vigente.</p>" : ""}
      ${isErp ? "<p>Notas técnicas, leiautes, schemas, regras de validação, Ajustes SINIEF/Atos COTEPE e mudanças (inclusive IBS/CBS) que exigem ajuste ou implementação em ERPs e emissores de documentos fiscais. Classificação automática: confirme sempre na publicação oficial.</p>" : ""}
      ${cat === "fiscal" ? "<p>Separação entre publicação oficial e notícia jornalística, e estágio de cada norma (projeto, consulta, aprovada, publicada, em vigor).</p>" : ""}
      </div></div>
      ${cat === "todas" ? `<div class="chips">${EXAMPLES.map((e) => `<button class="chip" data-q="${esc(e)}">${esc(e)}</button>`).join("")}</div>` : ""}
      <form class="filters" id="filters">
        <div class="periods" role="radiogroup" aria-label="Período de publicação">
          <span class="periods-label">Período</span>
          ${PERIODS.map(([v, label, title]) => `<label class="period ${String(f.period ?? "") === v ? "on" : ""}" title="${esc(title)}"><input type="radio" name="period" value="${esc(v)}" ${String(f.period ?? "") === v ? "checked" : ""}><span>${esc(label)}</span></label>`).join("")}
        </div>
        ${isAll ? `<select name="category" aria-label="Categoria">${opt("", "Todas as categorias", f.category)}${S.meta.categories.map((x) => opt(x.slug, x.name, f.category)).join("")}</select>` : ""}
        <select name="source" aria-label="Fonte">${opt("", "Todas as fontes", f.source)}${outlets}</select>
        <input type="date" name="from" value="${esc(f.from || "")}" aria-label="De" ${f.period === "custom" ? "" : "hidden"}>
        <input type="date" name="to" value="${esc(f.to || "")}" aria-label="Até" ${f.period === "custom" ? "" : "hidden"}>
        <select name="min_relevance" aria-label="Relevância">${opt("", "Qualquer relevância", f.min_relevance)}${opt("40", "Relevância média ou alta", f.min_relevance)}${opt("60", "Somente alta relevância", f.min_relevance)}</select>
        <label class="check" title="Receita, gov.br, Câmara, Senado, SEFAZ, CONFAZ, Comitê Gestor e outras fontes oficiais"><input type="checkbox" name="${fiscal ? "doc_type" : "official"}" value="${fiscal ? "oficial" : "1"}" ${(fiscal ? f.doc_type === "oficial" : f.official) ? "checked" : ""}> Somente oficiais</label>
        ${fiscal ? `<select name="legal_stage" aria-label="Estágio">${opt("", "Qualquer estágio", f.legal_stage)}${Object.entries(STAGES).map(([k, v]) => opt(k, v, f.legal_stage)).join("")}</select>` : ""}
        ${isErp ? `<select name="erp_doc" aria-label="Documento ou obrigação">${opt("", "Qualquer documento", f.erp_doc)}${ERP_DOCS.map((x) => opt(x, x, f.erp_doc)).join("")}</select>`
    : `<label class="check" title="Notas técnicas, leiautes, Ajustes SINIEF e mudanças que exigem ajuste em ERPs e emissores"><input type="checkbox" name="erp" value="1" ${f.erp ? "checked" : ""}> Exige ajuste em ERP</label>`}
        <span class="grow"></span>
        <select name="sort" aria-label="Ordenação">${q ? opt("auto", "Mais pertinentes à busca", f.sort || "auto") : ""}${opt("recent", "Mais recentes", f.sort)}${opt("relevance", "Mais relevantes", f.sort)}</select>
      </form>
      <p class="results-info" id="info"></p>
      <div class="grid" id="results"></div>
      <div class="more"><button class="btn" id="moreBtn" hidden>Carregar mais</button></div>`;

    const form = $("#filters");
    form.addEventListener("change", (ev) => {
      const data = new FormData(form);
      const p = new URLSearchParams();
      if (q) p.set("q", q);
      for (const [k, v] of data.entries()) if (v) p.set(k, v);
      if (ev.target.name === "period" && ev.target.value !== "custom") { p.delete("from"); p.delete("to"); }
      location.hash = `#/${base}${p.toString() ? "?" + p : ""}`;
    });
    view.querySelectorAll(".chip").forEach((b) => b.addEventListener("click", () => { location.hash = `#/todas?q=${encodeURIComponent(b.dataset.q)}`; }));

    const apiParams = new URLSearchParams();
    if (q) apiParams.set("q", q);
    apiParams.set("category", isAll ? (f.category || "todas") : cat);
    ["source", "min_relevance", "doc_type", "legal_stage", "erp_doc", "sort"].forEach((k) => f[k] && apiParams.set(k, f[k]));
    if (f.official) apiParams.set("official", "true");
    if (isErp || f.erp) apiParams.set("erp", "true");
    if (f.period && f.period !== "custom") {
      const start = periodStart(f.period);
      if (start) apiParams.set("from", start);
    } else if (f.period === "custom") {
      if (f.from) apiParams.set("from", f.from);
      if (f.to) apiParams.set("to", f.to);
    }
    let offset = 0;
    const load = async () => {
      apiParams.set("offset", offset); apiParams.set("limit", 30);
      const res = await api(`/api/articles?${apiParams}`);
      const box = $("#results");
      if (!res.items.length && offset === 0) {
        box.outerHTML = `<div class="empty" id="results">Nenhuma notícia encontrada${q ? ` para “${esc(q)}”` : ""}. Tente outros termos ou amplie o período.</div>`;
      } else {
        box.insertAdjacentHTML("beforeend", res.items.map(card).join(""));
        fixImages(box);
      }
      offset += res.items.length;
      const per = PERIODS.find(([v]) => v === (f.period || ""));
      const perTxt = f.period === "custom" ? ` · de ${f.from ? f.from.split("-").reverse().join("/") : "início"} até ${f.to ? f.to.split("-").reverse().join("/") : "hoje"}` : f.period && per ? ` · ${per[2].replace(/^Publicadas /, "publicadas ")}` : "";
      $("#info").textContent = `${res.total.toLocaleString("pt-BR")} notícia(s)${q ? ` para “${q}”` : ""}${perTxt} · ordenadas por ${f.sort === "relevance" ? "relevância" : f.sort === "recent" || !q ? "data de publicação" : "pertinência à busca"}`;
      $("#moreBtn").hidden = offset >= res.total;
    };
    $("#moreBtn").addEventListener("click", load);
    await load();
  }

  // ------------------------------------------------------------ detalhe
  async function openArticle(id) {
    const a = await api(`/api/articles/${id}`);
    const m = $("#modal");
    const list = (arr) => `<ul>${arr.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>`;
    const aiTag = a.provider && a.provider !== "regras" ? `IA (${esc(a.provider)})` : "regras automáticas";
    $("#modalBody").innerHTML = `
      <div class="hero" data-aid="${a.id}"><button class="icon-btn close" id="closeModal" aria-label="Fechar">${icon("close")}</button>${imageBlock(a)}</div>
      <div class="inner">
        ${badges(a, true)}
        <h2>${esc(a.title)}</h2>
        <div class="meta"><span class="outlet">${esc(a.outlet)}</span>${pubDate(a)}<span>· coletada em ${fmtLocal(a.collected_at)}</span></div>
        ${a.stage_note ? `<div class="notice">${esc(a.stage_note)}</div>` : ""}
        ${a.erp_impact ? `<div class="notice erp">Pode exigir ajuste em sistemas/ERP${(a.erp_docs || []).length ? ` (${esc(a.erp_docs.join(", "))})` : ""}: ${esc(a.erp_reason || "mudança técnica")}. Confira na publicação oficial a versão, os prazos de homologação e de produção.</div>` : ""}
        ${a.legal_stage && a.legal_stage !== "norma_em_vigor" && a.legislative ? `<div class="notice">Classificação automática. Confirme a situação da norma na publicação oficial antes de aplicar.</div>` : ""}
        ${a.summary ? `<h4>Resumo <span class="tag">${providerLabel(a)}</span></h4><p>${esc(a.summary)}</p>` : ""}
        ${a.summary_lang === "en" && (!a.provider || a.provider === "regras") ? `<p class="hint">Texto da fonte em inglês. A tradução e o resumo em português ficam disponíveis ao ligar a IA (veja o arquivo .env).</p>` : ""}
        ${a.key_points.length ? `<h4>Principais pontos <span class="tag">${a.provider && a.provider !== "regras" ? "IA" : "frases da fonte"}</span></h4>${list(a.key_points)}` : ""}
        ${a.impacts.length ? `<h4>Possíveis impactos para empresas e ERP <span class="tag">interpretação · ${aiTag}</span></h4>${list(a.impacts)}` : ""}
        ${a.legal_refs.length ? `<h4>Normas citadas <span class="tag">extraídas do texto</span></h4>${list(a.legal_refs)}` : ""}
        ${a.terms.length ? `<h4>Termos técnicos</h4><dl class="terms">${a.terms.map((t) => `<dt>${esc(t.term)}</dt><dd>${esc(t.explanation)}</dd>`).join("")}</dl>` : ""}
        ${a.related.length ? `<h4>Mesma notícia e atualizações</h4><ul>${a.related.map((r) => `<li>${r.is_update ? "<strong>Atualização:</strong> " : ""}<a href="${esc(safeUrl(r.url))}" target="_blank" rel="noopener noreferrer">${esc(r.title)}</a> — ${esc(r.outlet)}, ${r.published_at ? esc(r.published_at.length === 10 ? r.published_at.split("-").reverse().join("/") : fmtLocal(r.published_at)) : "data não confirmada"}</li>`).join("")}</ul>` : ""}
        <h4>Natureza do conteúdo</h4><p class="hint">${a.nature === "opiniao" ? "Opinião/coluna: reflete a visão do autor." : "Fato relatado pela fonte."} Resumo, pontos e impactos são interpretações automáticas e não substituem a leitura do original.</p>
        <p style="margin-top:18px"><a class="btn btn-primary" href="${esc(safeUrl(a.url))}" target="_blank" rel="noopener noreferrer">Abrir publicação original ${icon("external")}</a></p>
        <p class="hint">Fonte: ${esc(a.source_name || a.outlet)} · status: ${esc(a.validation_status)}${a.via_aggregator ? " · link original não confirmado (abre pelo Google Notícias)" : ""}</p>
      </div>`;
    fixImages(m);
    $("#closeModal").addEventListener("click", () => m.close());
    m.showModal();
  }

  // ------------------------------------------------------------ fontes e coleta
  async function viewSources(view) {
    const [sources, runs] = await Promise.all([api("/api/sources"), api("/api/runs?limit=50")]);
    const typeName = { rss: "RSS", html: "Página", search: "Busca" };
    view.innerHTML = `
      <div class="page-head"><div><h1>Fontes e coleta</h1><p>${sources.filter((s) => s.enabled).length} fontes ativas. ${STATIC ? "Coleta automática a cada hora pelo GitHub Actions." : `Atualização automática a cada ${S.status?.interval_min ?? 60} minutos (configurável no arquivo .env).`}</p></div></div>
      ${STATIC ? `<div class="panel"><h3>Adicionar fonte</h3><p class="hint">Nesta versão publicada, as fontes ficam no arquivo ${S.meta.repo ? `<a href="https://github.com/${esc(S.meta.repo)}/edit/main/config/sources.json" target="_blank" rel="noopener noreferrer">config/sources.json</a>` : "config/sources.json"} do repositório no GitHub. Ao salvar uma alteração nele, uma nova coleta roda e o site é publicado de novo em alguns minutos.</p></div>` : `<div class="panel"><h3>Adicionar fonte</h3>
        <form id="addForm" class="form-grid">
          <label>Nome<input name="name" required placeholder="Ex.: SEFAZ-MG notícias"></label>
          <label>Tipo<select name="type"><option value="rss">RSS / Atom</option><option value="search">Busca (Google Notícias)</option><option value="search-bing">Busca (Bing Notícias)</option><option value="html">Página sem RSS</option></select></label>
          <label>URL ou termo de busca<input name="target" required placeholder="https://… ou ICMS Minas Gerais"></label>
          <label>Categoria<select name="category">${S.meta.categories.map((c) => `<option value="${c.slug}">${esc(c.name)}</option>`).join("")}</select></label>
          <label>Padrão dos links (somente página)<input name="link_pattern" placeholder="Ex.: /noticias/20\\d\\d/"></label>
          <label class="check" style="flex-direction:row;align-items:center;margin-top:22px"><input type="checkbox" name="official"> Fonte oficial</label>
          <div style="display:flex;align-items:flex-end"><button class="btn btn-primary" type="submit">Testar e adicionar</button></div>
        </form>
        <p class="hint">A fonte é testada antes de ser salva. Para páginas sem RSS, informe uma expressão regular que os links das publicações atendem.</p>
      </div>`}
      <h3>Fontes</h3>
      <div class="table-wrap"><table><thead><tr><th>Fonte</th><th>Tipo</th><th>Categoria</th><th>Última coleta</th><th>Status</th><th>Itens</th><th>Próxima</th>${STATIC ? "" : "<th></th>"}</tr></thead><tbody>
      ${sources.map((s) => `<tr>
        <td><strong>${esc(s.name)}</strong>${s.official ? ` <span class="badge official">oficial</span>` : ""}<div class="hint">${esc(s.url || s.query || "")}</div></td>
        <td>${typeName[s.type] || s.type}${s.type === "search" ? ` · ${esc(s.options.engine || "google")}` : ""}</td>
        <td>${esc(catOf(s.category).name)}</td>
        <td>${fmtLocal(s.last_run_at)}</td>
        <td><span class="st ${esc(s.last_status || "")}">${esc(s.last_status || "aguardando")}</span>${s.last_error ? `<div class="hint" style="color:var(--bad)">${esc(s.last_error)}</div>` : ""}${s.consecutive_failures > 1 ? `<div class="hint">${s.consecutive_failures} falhas seguidas</div>` : ""}</td>
        <td>${s.items_total || 0}</td>
        <td>${fmtLocal(s.next_run_at)}</td>
        ${STATIC ? "" : `<td style="white-space:nowrap"><button class="btn btn-sm" data-collect="${esc(s.id)}">Coletar</button> <button class="btn btn-sm" data-toggle="${esc(s.id)}" data-enabled="${s.enabled}">${s.enabled ? "Desativar" : "Ativar"}</button></td>`}
      </tr>`).join("")}
      </tbody></table></div>
      <h3 style="margin-top:24px">Histórico das últimas atualizações</h3>
      <div class="table-wrap"><table><thead><tr><th>#</th><th>Início</th><th>Fim</th><th>Origem</th><th>Status</th><th>Fontes ok</th><th>Inalteradas</th><th>Com falha</th><th>Novas</th><th></th></tr></thead><tbody>
      ${runs.map((r) => `<tr><td>${r.id}</td><td>${fmtLocal(r.started_at)}</td><td>${fmtLocal(r.finished_at)}</td><td>${esc(r.trigger)}</td><td><span class="st ${esc(r.status)}">${esc(r.status)}</span></td><td>${r.sources_ok}</td><td>${r.sources_unchanged}</td><td>${r.sources_failed}</td><td>${r.new_items}</td><td><button class="btn btn-sm" data-run="${r.id}">Detalhes</button></td></tr>`).join("") || `<tr><td colspan="10">Nenhuma coleta registrada ainda.</td></tr>`}
      </tbody></table></div>`;

    view.querySelectorAll("[data-toggle]").forEach((b) => b.addEventListener("click", async () => {
      await api(`/api/sources/${b.dataset.toggle}`, { method: "PATCH", body: JSON.stringify({ enabled: b.dataset.enabled !== "1" }) });
      router();
    }));
    view.querySelectorAll("[data-collect]").forEach((b) => b.addEventListener("click", async () => {
      const r = await api(`/api/refresh?source=${encodeURIComponent(b.dataset.collect)}`, { method: "POST" });
      toast(r.started ? "Coleta da fonte iniciada." : r.message); pollStatus();
    }));
    view.querySelectorAll("[data-run]").forEach((b) => b.addEventListener("click", async () => {
      const logs = await api(`/api/runs/${b.dataset.run}`);
      $("#modalBody").innerHTML = `<div class="inner" style="padding-top:20px"><button class="icon-btn close" id="closeModal" aria-label="Fechar">${icon("close")}</button><h2>Coleta #${b.dataset.run}</h2>
        <div class="table-wrap"><table><thead><tr><th>Fonte</th><th>Status</th><th>HTTP</th><th>Itens lidos</th><th>Novos</th><th>Tempo</th><th>Erro</th></tr></thead><tbody>
        ${logs.map((l) => `<tr><td>${esc(l.source_name || l.source_id)}</td><td><span class="st ${esc(l.status)}">${esc(l.status)}</span></td><td>${l.http_status ?? ""}</td><td>${l.fetched_items}</td><td>${l.new_items}</td><td>${(l.duration_ms / 1000).toFixed(1)} s</td><td class="err">${esc(l.error || "")}</td></tr>`).join("")}
        </tbody></table></div></div>`;
      $("#closeModal").addEventListener("click", () => $("#modal").close());
      $("#modal").showModal();
    }));
    $("#addForm")?.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const fd = new FormData(ev.target);
      let type = fd.get("type"); const target = fd.get("target").trim();
      const body = { name: fd.get("name"), category: fd.get("category"), official: fd.get("official") === "on", options: {} };
      if (type.startsWith("search")) { body.type = "search"; body.query = target; body.options.engine = type === "search-bing" ? "bing" : "google"; }
      else { body.type = type; body.url = target; }
      if (type === "html") body.options.link_pattern = fd.get("link_pattern");
      const btn = ev.target.querySelector("button[type=submit]"); btn.disabled = true; btn.textContent = "Testando…";
      try { const r = await api("/api/sources", { method: "POST", body: JSON.stringify(body) }); toast(`Fonte adicionada: ${r.items_found} itens encontrados no teste.`); await loadMeta(); router(); }
      catch (e) { toast(e.message); btn.disabled = false; btn.textContent = "Testar e adicionar"; }
    });
  }

  // ------------------------------------------------------------ status e atualização
  async function pollStatus() {
    clearTimeout(pollStatus._t);
    try {
      const st = await api("/api/status");
      const was = S.status && S.status.running;
      S.status = st;
      const dot = $("#statusDot");
      dot.className = "dot " + (st.running ? "running" : st.health);
      const last = st.last_finished;
      $("#statusText").textContent = st.running
        ? `Coletando ${st.progress ? `${st.progress.done}/${st.progress.total} fontes` : "…"}`
        : last ? `Atualizado ${fmtLocal(last.finished_at)}` : "Sem coletas ainda";
      $("#statusBox").title = st.failing_sources.length ? `Fontes com falha: ${st.failing_sources.map((s) => s.name).join(", ")}` : "Todas as fontes responderam na última coleta";
      const btn = $("#refreshBtn");
      btn.disabled = st.running; btn.classList.toggle("spin", st.running);
      if (was && !st.running) { toast(`Coleta concluída: ${last ? last.new_items : 0} notícia(s) nova(s).`); await loadMeta(); router(); }
      if (st.data_changed) { toast("Novas notícias publicadas. A página foi atualizada."); await loadMeta(); if (!$("#modal").open) router(); }
      pollStatus._t = setTimeout(pollStatus, STATIC ? 300000 : st.running ? 4000 : 60000);
    } catch {
      $("#statusDot").className = "dot falhas"; $("#statusText").textContent = STATIC ? "Sem conexão" : "Servidor indisponível";
      pollStatus._t = setTimeout(pollStatus, 15000);
    }
  }
  async function loadMeta() {
    S.meta = await api("/api/meta");
    S.cats = Object.fromEntries(S.meta.categories.map((c) => [c.slug, c]));
    renderNav();
  }

  // ------------------------------------------------------------ tema e menu
  function applyTheme(t) { if (t) document.documentElement.dataset.theme = t; else delete document.documentElement.dataset.theme; }
  function closeMenu() { $("#sidebar").classList.remove("open"); $("#scrim").classList.remove("show"); }

  async function init() {
    hydrateIcons();
    applyTheme(store.get("radar-theme", ""));
    $("#themeBtn").addEventListener("click", () => {
      const dark = document.documentElement.dataset.theme ? document.documentElement.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
      const next = dark ? "light" : "dark"; applyTheme(next); store.set("radar-theme", next);
    });
    $("#menuBtn").addEventListener("click", () => { $("#sidebar").classList.add("open"); $("#scrim").classList.add("show"); });
    $("#scrim").addEventListener("click", closeMenu);
    $("#statusBox").addEventListener("click", () => { location.hash = "#/fontes"; });
    $("#refreshBtn").addEventListener("click", async () => {
      const r = await api("/api/refresh", { method: "POST" });
      toast(r.started ? "Atualização iniciada. Só o que mudou nas fontes será baixado." : r.message);
      if (r.reloaded) { await loadMeta(); router(); }
      setTimeout(pollStatus, 800);
    });
    $("#searchForm").addEventListener("submit", (ev) => {
      ev.preventDefault();
      const q = $("#searchInput").value.trim();
      const { path } = parseHash();
      const base = path.startsWith("c/") ? path : "todas";
      location.hash = `#/${base}${q ? "?q=" + encodeURIComponent(q) : ""}`;
    });
    document.addEventListener("click", (ev) => {
      const b = ev.target.closest("[data-open]");
      if (b) openArticle(b.dataset.open).catch((e) => toast(e.message));
    });
    $("#modal").addEventListener("click", (ev) => { if (ev.target.id === "modal") ev.target.close(); });
    window.addEventListener("hashchange", router);
    await loadMeta();
    pollStatus();
    router();
  }
  init();
})();
