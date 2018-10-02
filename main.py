
subs = {'sub_ticker':{'params':{'currencies':['test'],'symbols':['ethdai', 'ethbtc']}}, 'sub_trades':{'params':{'currencies':['this', 'that']}}}

for i in subs:
      print(getattr(i))
      for j in subs[i]['params']:
            for k in subs[i]['params'][j]:
                  print(j)
                  print(k)
