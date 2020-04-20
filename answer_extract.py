#! coding=utf-8
#! python = 3.6

from pyltp import Segmentor,SentenceSplitter
from math import log,sqrt
import OpenHowNet
import operator
import webFAQ
from vsm import VSM


class Tf_idf:
	__sentences = 	[]												# 存放句子实例，包括三个属性：该句子的 tf 表，句子文本，句子的分词结果,还有一个 score 得分域,用于排序
	__query_text = ""
	__query_words = []
	__vsm = None
	__segmentor = None
	__stop_words_list = []
	__hda = OpenHowNet.HowNetDict(use_sim=True)

	def __init__(self):
		# 加载分词模型
		model_path = "/home/skipper/myApps/ltp/ltp_data_v3.4.0/cws.model"
		self.__segmentor = Segmentor();
		self.__segmentor.load_with_lexicon(model_path,"data/customer_dict.txt");
		# 加载停用词文件,返回停用词列表
		with open("data/stop_words.txt",'r') as file_obj:
			for line in file_obj:
				self.__stop_words_list.append(line.rstrip())
		

	# 去除停用词
	def __del_stop_words(self,words):
		for word in self.__stop_words_list:
			if word in words:
				words.remove(word)


	# 计算两个词语相似度
	def __get_word_sim(self,w1,w2):
		return self.__hda.calculate_word_similarity(w1,w2)


	def __swin(self,sen_words,j,b):
		tf_idf,weight = 0,0
		tf = self.__vsm.caculate_tf(sen_words)
		for i in range(j,b+1):
			sw = sen_words[i]
			tf_idf += tf[sw] * self.__vsm.get_idf(sw)
			tmp = 0
			for w in self.__query_words:
				tmp = max(tmp,self.__get_word_sim(w,sw))
			weight += tmp

		return tf_idf * (weight+1)


	# 答案抽取模块（该模块若性能不好，或者要实现更加细致的“知识”抽取，并生成答案，那么可以直接更换此函数）
	# 而之前的两次过滤依然有效
	def __answer_extract(self,sentences):
		d = len(self.__query_words)
		for sentence in sentences:
			k = len(sentence['words'])
			sum = 0
			for j in range(k):
				sum += self.__swin(sentence['words'],j,min(j+d,k-1))
			sentence['score'] = sum

		res_list = sorted(sentences,key=lambda x : x['score'],reverse=True)	# 按照关键词过滤得分从高到低排序

		return res_list[:5]


	# 融入语义的 VSM 第二次过滤
	def __filter_by_vsm(self,sentences):

		self.__vsm = VSM()
		self.__vsm.init(sentences,self.__hda)
		sentences = self.__vsm.sim_of_all_sentence(self.__query_words)
		res_list = sorted(sentences,key=lambda x : x['score'],reverse=True)	# 按照关键词过滤得分从高到低排序

		# test
		# for sentence in res_list:
		# 	print('(',sentence['text'],end='')
		# 	for w in sentence['words']:
		# 		print(w,end=',')
		# 	print('cosa: ',sentence['score'],end='')
		# 	print(')',end='\n')
		#

		return res_list[:100] 


	# 关键词(扩展关键词）第一次过滤
	def __filter_by_keywords(self,sentences):
		self.__query_words = list(self.__segmentor.segment(self.__query_text))
		self.__del_stop_words(self.__query_words)
		for sentence_item in sentences:										# sentences 中每一个句子项
			for keywords in self.__query_words:
				for words in sentence_item['words']:
					if self.__get_word_sim(keywords,words) >= 0.92:			# 两个词语义相似度阀值
						sentence_item['score'] += 1
		res_list = sorted(sentences,key=lambda x : x['score'],reverse=True)	# 按照关键词过滤得分从高到低排序

		if len(res_list) >= 300:
			return res_list[:300]											# 返回得分高的前 300 个
		else:
			return res_list


	# 将语料文本全部分句、分词处理
	def __split_sentences(self,text_data):
		sentences = []														# 注意和 __sentences 区分哦
		sentence_list = SentenceSplitter.split(text_data)					# 分句
		for sentence_text in sentence_list:										# 逐个句子进行分句，并构造一个 res_sentence 便于处理
			res_sentence = {}
			if sentence_text[-1] is '？':											# 去除问句
				continue
			words = list(self.__segmentor.segment(sentence_text))				# 分词
			self.__del_stop_words(words)									# 去除停用词
			res_sentence['text'],res_sentence['words'],res_sentence['score'] = sentence_text,words,0
			sentences.append(res_sentence)

		return sentences														# 返回构造的句子列表


	# 尝试从数据库获得答案，如果数据库中没有合适答案，从 web 语料库中抽取答案
	def __get_answer_from_database(self):

		pass

		return None															# 暂时不处理数据库，先使用 web 语料库(如果我有 百度知道 的数据库那么就不需要 web 语料库了：）)


	# 从 web 语料库抽取答案
	def __get_answer_from_web(self):
		# text_data = webFAQ.get_baiduzd_faq(query_sentence)				# 从百度知道爬取答案
		# 方便起见，直接先将 web 语料硬编码。因为爬取模块我没有设置代理服务器，所以爬取会很慢
		# text_data 给出形式为事实性文本，一个字符串。现在文本来源是百度知道相关问题的一些答案组成的文本。（之后可能考虑使用文档检索工具再进行网页文档检索来增加语料的规模）
		# text_data = """汶川地震是8级。5·12汶川地震严重破坏地区超过10万平方千米，其中，极重灾区共10个县(市)，较重灾区共41个县(市)，一般灾区共186个县(市)。截至2008年9月18日12时，5·12汶川地震共造成69227人死亡，374643人受伤，17923人失踪，是中华人民共和国成立以来破坏力最大的地震。也是唐山大地震后伤亡最严重的一次地震。截至2009年5月25日10时，共遇难69227人(实际应该为八万多人)，受伤374643人，失踪17923人。其中四川省68712名同胞遇难，17921名同胞失踪，共有5335名学生遇难或失踪。直接经济损失达8451亿元。是中华人民共和国自建国以来影响最大的一次地震。里氏震级8.0级，矩震级8.3级。北京时间（UTC+8）2008年5月12日（星期一）14时28分04秒，根据中华人民共和国地震局的数据，此次地震的面波震级里氏震级达8.0Ms、矩震级达8.3Mw（根据美国地质调查局的数据，矩震级为7.9Mw），地震烈度达到11度。此次地震的地震波已确认共环绕了地球6圈。地震烈度：汶川地震的震中烈度高达11度，汶川地震的10度区面积则为约3144平方千米，呈北东向狭长展布，东北端达四川省青川县，西南端达汶川。以四川省汶川县映秀镇和北川县县城两个中心呈长条状分布，面积约2419平方千米。其中，映秀11度区沿汶川——都江堰——彭州方向分布，北川11度区沿安县——北川——平武方向分布。汶川地震发生后，中国国家地震局最初发布是7.6级，后更改为8.0级，之后又确定为7.8，18日，中国地震局再一次将地震级数修正为8.0级，这次修订是综合全球地震台网在内的更多台站资料，里氏8.0是最终修订值，。里氏震级8.0级，矩震级8.3级。5·12汶川地震，发生于北京时间（UTC+8）2008年5月12日（星期一）14时28分04秒，震中位于中华人民共和国四川省阿坝藏族羌族自治州汶川县映秀镇与漩口镇交界处。根据中国地震局的数据，此次地震的面波震级达8.0Ms、矩震级达8.3Mw（根据美国地质调查局的数据，矩震级为7.9Mw），地震烈度达到11度。地震波及大半个中国及亚洲多个国家和地区，北至辽宁，东至上海，南至香港、澳门、泰国、越南，西至巴基斯坦均有震感。9度以上地区破坏极其严重，其分布区域紧靠发震断层，沿断层走向成长条形状。其中，10度和9度区的边界受龙门山前山断裂错动的影响，在绵竹市和什邡市山区向盆地方向突出，在都江堰市区也略有突出。起先申报的是7.8级，随后实际震级为8.0级。我为中国地震局华中地震检测室统计员，回答准确性为100%。汶川大地震，根据中华人民共和国地震局的数据，此次地震的面波震级是里氏震级达8.0Ms、矩震级达8.3Mw（根据美国地质调查局的数据，矩震级为7.9Mw），地震烈度达到11度。5·12汶川地震严重破坏地区超过10万平方千米，其中，极重灾区共10个县（市），较重灾区共41个县（市），一般灾区共186个县（市）。截至2008年9月18日12时，5·12汶川地震共造成69227人死亡，374643人受伤，17923人失踪，汶川大地震是我国成立以来破坏力最大的地震，也是唐山大地震后伤亡最严重的一次地震。地震波及大半个中国及亚洲多个国家和地区，北至辽宁，东至上海，南至香港、澳门、泰国、越南，西至巴基斯坦均有震感。汶川地震震级最高是8.0级。5·12汶川地震是于2008年5月12日14时28分04秒，四川省阿坝藏族羌族自治州汶川县发生的8.0级地震，地震造成69227人遇难，374643人受伤，17923人失踪。汶川大地震最高级为8级地震时间为2008年5月12日28分04秒，这场地震造成了69227人收到灾难374643人伤，17923人失踪，导致经济损失极大严重！名称：5·12汶川地震时间：2008年5月12日14时28分04秒地理位置：四川汶川、北川震中经纬度：30.986°N103.364°E震源深度：14km震级：里氏震级8.0级，矩震级7.9级震中烈度：11度伤亡人数：遇难:69142人失踪:17551人。如果你去新闻上面了解一下吧，新闻上报道过，好像最高是八级吧？5·12汶川地震的面波震级达8.0Ms、矩震级达8.3Mw。（根据美国地质调查局的数据，矩震级为7.9Mw），地震烈度达到11度。地震波及大半个中国及亚洲多个国家和地区，北至辽宁，东至上海，南至香港、澳门、泰国、越南，西至巴基斯坦均有震感。5·12汶川地震严重破坏地区超过10万平方千米，其中，极重灾区共10个县（市），较重灾区共41个县（市），一般灾区共186个县（市）。截至2008年9月18日12时，5·12汶川地震共造成69227人死亡，374643人受伤，17923人失踪，是中华人民共和国成立以来破坏力最大的地震，也是唐山大地震后伤亡最严重的一次地震。经国务院批准，自2009年起，每年5月12日为全国“防灾减灾日”。2018年5月，中国扶贫基金会公布汶川地震资金物资使用情况，救援项目全部完成。里氏震级8.0级，矩震级8.3级1.时间位置：5·12四川汶川特大地震是公元2008年5月12日14时28分04秒（星期一，农历戊子鼠年四月大初八日）发生的8.0级（最大震级14.0级）地震，震中位于四川省汶川县映秀镇与漩口镇交界处（渔子溪长城（中国长城世界遗产）正西方向2.5公里处，牛眠沟莲花心山脚下），东经103°42'，北纬31°01'（美国地质调查局则认可汶川地震发生地点为北纬30.986゜026.25′214.3162″，东经103.364゜276.60′333.0260″）。2.发生原因：由于印度洋板块在以每年约15cm的速度向北移动，使得亚欧板块受到压力，并造成青藏高原快速隆升。又由于受重力影响，青藏高原东面沿龙门山在逐渐下沉，且面临着四川盆地的顽强阻挡，造成构造应力能量的长期积累。最终压力在龙门山北川至映秀地区突然释放。造成了逆冲、右旋、挤压型断层地震。四川特大地震发生在地壳脆韧性转换带，震源深度为10～20千米，与地表近，持续时间较长（约2分钟），因此破坏性巨大，影响强烈。此次地震的面波震级达8.0级。地震烈度达到11度。地震波及大半个中国及亚洲多个国家和地区，北至辽宁，东至上海，南至香港、澳门、泰国、越南，西至巴基斯坦均有震感。中国地质科学院地质力学所基础地质研究室专家冯梅做客国土资源部门户网时分析指出，汶川地震破坏性强于唐山地震。第一、从震级上可以看出，汶川地震稍强。唐山地震国际上公认的是7.8级，汶川地震是8.0级。第二、从地缘机制断层错动上看，唐山地震是拉张性的，是上盘往下掉。汶川地震是上盘往上升，要比唐山地震影响大。第三、唐山地震的断层错动时间是12.9秒，5·12汶川地震汶川地震是22.2秒，错动时间越长，人们感受到强震的时间越长，也就是说汶川地震建筑物的摆幅持续时间比唐山地震要强。第四、从地震张量的指数上看，唐山地震是7.2级，汶川地震是9.4级，差别很大。第五、汶川地震波及的面积、造成的受灾面积比唐山地震大。冯梅说，这主要是由于断层错动的原因，汶川地震是挤压断裂，错动方向是北东方向，也就是说汶川的北东方向受影响比较大，但是它的西部情况就会好一些。最先国家对外公布的是7.8级，实际最终公布为8.0级。其原因是按照国际法的规定，8.0级地震世界各国可以直接实施国际援助，国家考虑到地震灾区有很多国家的军事基地，因此，早先公布为7.8级。这是非常高的地震级别了哈。已经很高了。。至少在中国。和当年的唐山大地震一个震级。。里氏7。8级。。世界上最高震级科学家公认最大地震为8.9级。但那次地震可定为8.9级呢？众说纷云。有人认为1960年5月22日19时11分发生在南美智利的那次地震最大，震级达到8.9级。还有人认为1906年1月31日南美厄瓜多尔一哥伦比亚边界附近海中发生的那次地震最大，震级达到8.9级。也有人认为1933年3月3日日本三陆东边海中发生的地震最大，震级是8.9级。但也有不同的观点。1933年日本三陆地震，日本人自己推算只有8.5级。1906年厄瓜多尔一哥伦比亚边界附近海中那次地震，一般也只定为8.6级。1960年智利那次大地震，也有人定为8.5级或8.75级，甚至还有人定为8.3级，列为一般大地震的。值得指出，1960年智利大地震前后，在短短一天半的时间里，7级以上大地震至少发生了5次，其中3次达到或超过8级。如果把整个地震过程统一起来看，智利大地震规模之大，释放能量之多，堪称罕见的特大地震。汶川地震是8.0级的地震。5·12汶川地震，发生于北京时间(UTC+8)2008年5月12日(星期一)14时28分04秒，根据中华人民共和国地震局的数据，此次地震的面波震级达8.0Ms、矩震级达8.3Mw(根据美国地质调查局的数据，矩震级为7.9Mw)，地震烈度达到11度。地震波及大半个中国及亚洲多个国家和地区，北至辽宁，东至上海，南至香港、澳门、泰国、越南，西至巴基斯坦均有震感。5·12汶川地震严重破坏地区超过10万平方千米，其中，极重灾区共10个县(市)，较重灾区共41个县(市)，一般灾区共186个县(市)。截至2008年9月18日12时，5·12汶川地震共造成69227人死亡，374643人受伤，17923人失踪，是中华人民共和国成立以来破坏力最大的地震，也是唐山大地震后伤亡最严重的一次地震。四川，汶川大地震，发生于北京时间2008年5月12日5·12汶川地震14时28分04.1秒（协调世界时5月12日14时28分04.1秒），震中位于中国四川省阿坝藏族羌族自治州汶川县境内、四川省省会成都市西北偏西方向90千米处。根据中国地震局的数据，此次地震的面波震级达8.0Ms、矩震级达8.。汶川地震的面波震级里氏震级达8.0Ms、矩震级达8.3Mw（根据美国地质调查局的数据，矩震级为7.9Mw），地震烈度达到11度。此次地震的地震波已确认共环绕了地球6圈。地震波及大半个中国及亚洲多个国家和地区，北至辽宁，东至上海，南至香港、澳门、泰国、越南，西至巴基斯坦均有震感。截至2008年9月18日12时，5·12汶川地震共造成69227人死亡，374643人受伤，17923人失踪，是中华人民共和国成立以来破坏力最大的地震，也是唐山大地震后伤亡最严重的一次地震。扩展资料5·12汶川地震对四川省文物造成一定影响，受损文物约占全省文物五分之一。绵阳市8处国家级重点文物保护单位，有5处严重受损，30个省级文保单位，24个受损。其中平武县有3500年历史的报恩寺损毁严重。都江堰40余处古建筑中，有95%在这次地震中受损，其中受损最严重的，除了泰安寺还有二王庙、伏龙观、青城山天师洞的皇帝殿等。阿坝州80%到90%的藏羌碉楼可能已经受损，桃坪羌寨局部垮塌。参考资料来源：百度百科-5·12汶川地震。2008年5月12日14时28分04秒，四川汶川、北川，8级强震猝然袭来，大地颤抖，山河移位，满目疮痍，生离死别……西南处，国有殇。这是新中国成立以来破坏性最强、波及范围最大的一次地震。此次地震重创约50万平方公里的中国大地！为表达全国各族人民对四川汶川大地震遇难同胞的深切哀悼，国务院决定，2008年5月19日至21日为全国哀悼日。自2009年起，每年5月12日为全国防灾减灾日。名称：5·12汶川地震时间：2008年5月12日14时28分04秒地理位置：震中心为四川省汶川县映秀镇，其次为北川，都江堰市西21km，崇州市西北48km,大邑县西北48km,成都市西北75km震中经纬度：北纬30.986°，东经103.364°震源深度：14km震级：里氏震级8.0级，矩震级7.9级震中烈度：最大11度伤亡人数：。2008年5月12日14时28分04秒，四川汶川、北川，8级强震猝然袭来，大地颤抖，山河移位，满目疮痍，生离死别……西南处，国有殇。这是新中国成立以来破坏性最强、波及范围最大的一次地震。此次地震重创约50万平方公里的中国大地！为表达全国各族人民对四川汶川大地震遇难同胞的深切哀悼，国务院决定，2008年5月19日至21日为全国哀悼日。自2009年起，每年5月12日为全国防灾减灾日。查看词条图册名称：5·12汶川地震时间：2008年5月12日14时28分04秒地理位置：震中心为四川省汶川县映秀镇，其次为北川,都江堰市西21km,崇州市西北48km,大邑县西北48km,成都市西北75km震中经纬度：北纬30.986°，东经103.364°震源深度：14km震级：里氏震级8.0级，矩震级7.9级震中烈度：最大11度伤亡人数：69227人遇难，374643人受伤，失踪17923人地震类型：构造地震。2008年5月12日14时28分04秒，四川汶川、北川，8级强震猝然袭来，大地颤抖，山河移位，满目疮痍，生离死别……西南处，国有殇。这是新中国成立以来破坏性最强、波及范围最大的一次地震。此次地震重创约50万平方公里的中国大地！为表达全国各族人民对四川汶川大地震遇难同胞的深切哀悼，国务院决定，2008年5月19日至21日为全国哀悼日。自2009年起，每年5月12日为全国防灾减灾日。名称：5·12汶川地震时间：2008年5月12日14时28分04秒地理位置：震中心为四川省汶川县映秀镇，其次为北川，都江堰市西21km，崇州市西北48km,大邑县西北48km,成都市西北75km震中经纬度：北纬30.986°，东经103.364°震源深度：14km震级：里氏震级8.0级，矩震级7.9级震中烈度：最大11度伤亡人数：。刚开始说是7.8级，后面修正为8.0级。时间：2008年5月12日14时28分04.0秒纬度：31.0°N经度：103.4°E深度：33km震级：里氏8.0级最大烈度：11度震中位置：四川汶川县映秀镇都江堰市西21km(267°)崇州市西北48km(327°)大邑县西北48km(346°)成都西北75km(302°)历史背景：汶川地震是中国自我国建国以来最为强烈的一次地震，直接严重受灾地区达10万平方公里地震成因：中科院地质与地球物理研究所研究员、青藏高原研究专家王二七对汶川地区地质构造比较熟悉，5月上旬刚去过汶川地区。他分析说，汶川地震发生在青藏高原的东南边缘、川西龙门山的中心，位于汶川——茂汶大断裂带上。印度洋板块向北运动，挤压欧亚板块、造成青藏高原的隆升。高原在隆升的同时，也同时向东运动，挤压四川盆地。四川盆地是一个相对稳定的地块。虽然龙门山主体看上去构造活动性不强，但是可能是处在应力的蓄积过程中，蓄积到了一定程度，地壳就会破裂，从而发生地震。美国地质勘探局发布的消息也认为，这次地震的震中和震源机制与龙门山断裂带或者某个相关构造断层的运动相吻合，地震是一个逆冲断层向东北方向运动的结果。从大。中国地震局于5月18日已将汶川地震震级从7.8级修订为8级印度板块向亚洲板块俯冲，造成青藏高原快速隆升。高原物质向东缓慢流动，在高原东缘沿龙门山构造带向东挤压，遇到四川盆地之下刚性地块的顽强阻挡，造成构造应力能量的长期积累，最终在龙门山北川——映秀地区突然释放。逆冲、右旋、挤压型断层地震。发震构造是龙门山构造带中央断裂带，在挤压应力作用下，由南西向北东逆冲运动；这次地震属于单向破裂地震，由南西向北东迁移，致使余震向北东方向扩张；挤压型逆冲断层地震在主震之后，应力传播和释放过程比较缓慢，可能导致余震强度较大，持续时间较长。是浅源地震。汶川地震不属于深板块边界的效应，发生在地壳脆——韧性转换带，震源深度为１０千米——２０千米，因此破坏性巨大。专家表示，全球7级以上地震每年18次，8级以上1－2次。我国受印度板块和太平洋板块推挤，地震活动比较频繁。张国民说，从大的方面来说，汶川地震处于我国一个大地震带－－南北地震带上，中部地区的中轴地震带位于经度100度到105度之间，涉及地区包括从宁夏经甘肃东部、四川西部、直至云南，属于我国的地震密集带。从小的方面说，汶川又在四川的龙门山地震带上。因此。8.0级！里氏8.0级。里氏震级8.0级，矩震级8.3级5·12汶川地震，发生于北京时间（UTC+8）2008年5月12日（星期一）14时28分04秒，根据中华人民共和国地震局的数据，此次地震的面波震级里氏震级达8.0Ms、矩震级达8.3Mw（根据美国地质调查局的数据，矩震级为7.9Mw），地震烈度达到11度。此次地震的地震波已确认共环绕了地球6圈[1]。地震波及大半个中国及亚洲多个国家和地区，北至辽宁，东至上海，南至香港、澳门、泰国、越南，西至巴基斯坦均有震感。5·12汶川地震严重破坏地区超过10万平方千米，其中，极重灾区共10个县（市），较重灾区共41个县（市），一般灾区共186个县（市）。截至2008年9月18日12时，5·12汶川地震共造成69227人死亡，374643人受伤，17923人失踪，是中华人民共和国成立以来破坏力最大的地震，也是唐山大地震后伤亡最严重的一次地震。经国务院批准，自2009年起，每年5月12日为全国“防灾减灾日”。[2]。当时看新闻好像是8.0级。2008年汶川大地震属8.0级时间：2008年5月12日14时28分04.0秒纬度：31.0°N经度：103.4°E深度：33km震级：里氏8.0级（中国地震局于5月18日已将汶川地震震级从7.8级修订为8级）最大烈度：11度震中位置：四川汶川县映秀镇都江堰市西21km（267°）崇州市西北48km（327°）大邑县西北48km（346°）成都西北75km（302°）历史背景：汶川地震是中国自我国建国以来最为强烈的一次地震，直接严重受灾地区达10万平方公里。扩展资料发生原因由于印度洋板块在以每年约15cm的速度向北移动，使得亚欧板块受到压力，并造成青藏高原快速隆升。又由于受重力影响，青藏高原东面沿龙门山在逐渐下沉，且面临着四川盆地的顽强阻挡，造成构造应力能量的长期积累。最终压力在龙门山北川至映秀地区突然释放。造成了逆冲、右旋、挤压型断层地震。四川特大地震发生在地壳脆韧性转换带，震源深度为10～20千米，与地表近，持续时间较长（约2分钟），因此破坏性巨大，影响强烈。参考资料来源：百度百科-5·12汶川地震。汶川地震震级最高是8.0级。5·12汶川地震是于2008年5月12日14时28分04秒，四川省阿坝藏族羌族自治州汶川县发生的8.0级地震，地震造成69227人遇难，374643人受伤，17923人失踪。5·12汶川地震，发生于北京时间（UTC+8）2008年5月12日（星期一）14时28分04秒，位于中国四川省阿坝藏族羌族自治州汶川县映秀镇与漩口镇交界处。根据中国地震局的数据，地震的面波震级达8.0Ms、矩震级达8.3Mw（根据美国地质调查局的数据，矩震级为7.9Mw），地震烈度达到了11度。希望我的回答能够帮助到你。北京时间2008年5月12日14时28分，在四川汶川县（北纬31．0度，东经103．4度）发生7．6级地震。根据记者第一时间不完全统计，海南、云南、四川、湖南、重庆、江西、湖北、北京、甘肃、山西、内蒙古都不同程度感觉到了震感。武汉震感强烈，在房屋内可以感觉到明显的晃动，几分钟后大街上到处都是出来躲避的人们。地震分级，分为12等级：第一级，人们并未感觉到震动。第二级，人在高楼才能感觉晃动。第三级，在地面的室内能感觉到，悬挂对象也晃动。第四级，连汽车也晃动，严重的话木墙或窗架会出现裂缝。第五级，容器中的液体溅出，睡觉的人会被震醒，小物体会移位。第六级，墙上挂的图画会掉下，家具移动，人们会因为害怕纷纷逃到屋外。第七级，人会站立不稳，池塘出现水波。第八级，砖石墙部分破裂倒塌，树枝断落。第九级，是很严重的，地下水管破裂，地面出现裂缝，小建筑物倒塌等等。第十级，水库出现裂缝、桥梁被破坏，铁路扭曲等。第十一级，地下水管及阴沟系统全被破坏。第十二级，全面破坏，连巨石也震动移位。最先国家对外公布的是7.8级，实际最终公布为8.0级。其原因是按照国际法的规定，8.0级地震世界各国可以直接实施国际援助，国家考虑到地震灾区有很多国家的军事基地，因此，早先公布为7.8级。这是非常高的地震级别了哈。已经很高了。。至少在中国。和当年的唐山大地震一个震级。。里氏7。8级。。世界上最高震级科学家公认最大地震为8.9级。但那次地震可定为8.9级呢？众说纷云。有人认为1960年5月22日19时11分发生在南美智利的那次地震最大，震级达到8.9级。还有人认为1906年1月31日南美厄瓜多尔一哥伦比亚边界附近海中发生的那次地震最大，震级达到8.9级。也有人认为1933年3月3日日本三陆东边海中发生的地震最大，震级是8.9级。但也有不同的观点。1933年日本三陆地震，日本人自己推算只有8.5级。1906年厄瓜多尔一哥伦比亚边界附近海中那次地震，一般也只定为8.6级。1960年智利那次大地震，也有人定为8.5级或8.75级，甚至还有人定为8.3级，列为一般大地震的。值得指出，1960年智利大地震前后，在短短一天半的时间里，7级以上大地震至少发生了5次，其中3次达到或超过8级。如果把整个地震过程统一起来看，智利大地震规模之大，释放能量之多，堪称罕见的特大地震。汶川地震为8.0级大地震。汶川大地震，发生于北京时间2008年5月12日14时28分04.1秒，震中位于中国四川省阿坝藏族羌族自治州汶川县境内、四川省省会成都市西北偏西方向90千米处。根据中国地震局的数据，此次地震的面波震级达8.0Ms、矩震级达8.3Mw，破坏地区超过10万平方公里。地震烈度可能达到11级。地震波及大半个中国及多个亚洲国家。北至北京，东至上海，南至香港、泰国、台湾、越南，西至巴基斯坦均有震感。汶川大地震是中国一九四九年以来破坏性最强、波及范围最大的一次地震，地震的强度、烈度都超过了1976年的唐山大地震。5月12日，据新华社报道四川汶川发生7.6级大地震。新民网记者立即拨打了位于成都的四川省地震局的电话，地震局向记者确认根据省地震局监测，四川汶川县发生8.0级大地震。先是7.6级然后修订为7.8。现在又变成了8.0级别。估计还要被修改。地震震级8.0,地震烈度11度!一般地区房屋设计要求能禁受地震烈度为7度今天刚看的报纸。8.0级。"""
		text_data = """1、塑料袋包装的牛奶保质期一般为一个月。这种包装经济实惠，但其材料较薄，容易出现破包。2、百利包装的牛奶保质期从1个月到6个月不等。百利包内层为热封层，添加黑色母料起到阻挡光线的作用；中间层和外层印刷层添加白母料起到遮盖黑色和阻隔光线的作用。扩展资料牛奶注意事项牛奶与菠菜相克：同食会引起痢疾。牛奶与果汁相克：果汁属于酸性饮料，能使蛋白质凝结成块影响吸收，降低牛奶的营养。牛奶中含有丰富的蛋白质。果子露属酸性钵料，在胃中能使蛋白质凝固成块，从而直接影响人对蛋白质的吸收，降低牛奶的营养价值，而且还会出现腹泻、腹痛和腹胀等症。牛奶与橘子相克：刚喝完牛奶就吃橘子，影响消化吸收，而且还会使人腹胀、腹痛、腹泻。牛奶中所含的蛋白质遇到桔子的果酸便会凝固，影响蛋白质的消化吸收，因此在吃桔子时不宜喝牛奶。参考资料来源：百度百科——牛奶参考资料来源：人民网——牛奶和10种食物不能同吃选择牛奶有妙招。说了一大片，净是废话，主题再那里？我问牛奶的保质期有多久的。东扯西扯的！问你保质期多久，你发那么多比比啥，。牛奶分为两大类目前市场上的牛奶，大部分都属于杀菌乳，也就是我们常说的消毒奶。别看牛奶的包装上名称各异，什么“纯鲜牛奶”、“鲜牛奶”、“常温奶”，其实，从杀菌方法上来说，基本上就分两大类。一是巴氏杀菌乳，就是我们常见的“巴氏消毒奶”。顾名思义，就是采取“巴氏杀菌法”进行杀菌的牛奶。所谓“巴氏杀菌法”，就是在较长的时间内，用低温杀死牛奶中的致病菌，保留对人体有益的细菌。不过，由于这种方法不能消灭牛奶中所有的微生物，因此产品需要冷藏，保质期也比较短，一般只有几天，大家昵称为房子牛奶的鲜奶就属于此。另一种叫灭菌乳，是采用高温将牛奶中的细菌全部杀死。由于牛奶中一点微生物都不存在了，因此可在常温下保存，而且保质期比较长，一般可达3个月以上，大家昵称为袋装牛奶的纯奶就属于此。牛奶保质期短更新鲜，低温杀菌保留营养多！巴氏杀菌乳由于保存的营养成分较多，常被厂家叫做“鲜奶”。其实，杀菌时不管是低温还是高温，都会对牛奶的营养价值造成一定的影响，而真正的鲜奶应是没有经过加工的牛奶。在我们的市场里基本上没有生鲜牛奶，这种牛奶是未经杀菌的。巴氏消毒奶是规定时间内以不太高的温度处理液体食品的一种加热。二楼说的对，，。纯牛奶保质期可达6至9个月。牛奶保质期的长短是由杀菌方式决定的。根据不同的杀菌方式，可以将牛奶分为巴氏杀菌奶、高温巴氏杀菌奶和超高温灭菌奶。通常情况下，需冷藏保存且保质期在三天左右的牛奶属于巴氏杀菌奶，这种牛奶经过低温杀菌处理，既能保留牛奶中对人体有利的细菌、杀死对人体有害的微生物，同时也能保持牛奶的营养与鲜度。无需冷藏的牛奶也被称为纯牛奶，通常采用超高温杀菌处理，超高温杀菌即经过4-15秒135-152°C的瞬间灭菌处理将牛奶中的细菌全部杀死，这类乳制品的保质期通常可达6至9个月。经过更高温杀菌的牛奶保质期更长。在不同的杀菌方式中，巴氏杀菌奶的营养成分得到了最好的保存，但因为其对储藏条件要求较高，因此价格也相对更高。如果条件允许，巴氏杀菌奶是最好的选择。扩展资料：选购牛奶时要注意以下几点：1、尽量选购日期新的大品牌牛奶，开封后尽快饮用。2、高钙牛奶适合孕妇、哺乳期女性以及50岁以上消费者，牛奶本身钙含量较高，普通成年人不需要刻意增加钙的摄入。3、低脂牛奶、脱脂牛奶适合需要控制脂肪摄入量的消费者，如患有高血脂、高血压、脑血栓等心脑血管系统疾病，以及糖尿病、肥胖等代谢性疾病的人。脂肪是人。纯牛奶保质期一般为45天。牛奶含有丰富的矿物质、钙、磷、铁、锌、铜、锰、钼。最难得的是，牛奶是人体钙的最佳来源，而且钙磷比例非常适当，利于钙的吸收。种类复杂，至少有100多种，主要成份有水、脂肪、磷脂、蛋白质、乳糖、无机盐等。保存方法：（1）鲜牛奶应该立刻放置在阴凉的地方，最好是放在冰箱里。（2）不要让牛奶曝晒或照射灯光，日光、灯光均会破坏牛奶中的数种维生素，同时也会使其丧失芳香。（3）瓶盖要盖好，以免他种气味串入牛奶里。（4）牛奶倒进杯子、茶壶等容器，如没有喝完，应盖好盖子放回冰箱，切不可倒回原来的瓶子。（5）过冷对牛奶亦有不良影响。当牛奶冷冻成冰时，其品质会受损害。因此，牛奶不宜冷冻，放入冰箱冷藏即可。打的鲜牛奶一般2天左右.简装牛奶一般保质:3~5天.精装(冷灌)牛奶一般20~35天.在喝牛奶前一定要先烧开再喝,因为有些地区不经常食用牛奶,凉喝牛奶会有排斥~!如果喝纯奶腹泻,那么就只能喝酸奶或奶茶~对于9个月保质期的牛奶......你看着办吧~。那要看变质没？应该放到阴凉的地方最好1个月就把他全部喝掉。纯牛奶的保质期怎么可能9个月？不要再喝了！据我所知，纯牛奶的保质期也就21天左右。袋装的鲜牛奶保质期一般为三天，消费者在购买时应先看清生产日期，尽量选择当天生产的牛奶，过期的不要购买。产品的保质期是指产品的最佳食用期。产品的保质期由生产者提供，标注在限时使用的产品上。在保质期内，产品的生产企业对该产品质量符合有关标准或明示担保的质量条件负责，销售者可以放心销售这些产品，消费者可以安全使用。专家介绍说，目前市场上销售的液态奶主要是巴氏消毒奶(即杀菌奶)和超高温消毒奶(即UHT灭菌奶)。前者是指将鲜奶加热到75℃到80℃温度下,瞬间杀死致病微生物，保留有益菌群，充分保持鲜奶的营养与鲜度，其优点是对营养物质的破坏少，缺点是保存时间短。后者是指在135℃到150℃的温度下，进行4到15秒的瞬间灭菌处理，完全破坏其中可生长的微生物和芽孢，其优点是牛奶可在常温下保存较长时间，缺点是高温破坏了很多营养物质。根据国际乳业联合会(IDF)的研究数据，用UHT灭菌法生产的牛奶中维生素、氨基酸的损失率，乳清蛋白的变性率都远远高于巴氏杀菌法。消费者如何区别两种奶?牛奶不是保存越久越好，保质期7天以内的袋装、新鲜屋、玻璃瓶等产品属于营养价值较高的巴氏消毒奶，需要冷藏；保质期30天以上的袋装、无菌砖、无菌枕包装的产品就属于UHT灭菌奶，无需冷藏，也就是通常说的常温奶。专家建议在条件许可的情况下，市民还是应该喝新鲜的有营养的巴氏消毒奶。在冷藏条件不成熟，比如需要长期储存或长途旅行，那么UHT牛奶就是最好的营养饮料了。而且国家已经做出规定，包装上必须。牛奶的保质期有三个月.。有的是30天，有的是45天。30--45天。蒙牛的牛奶也分很多类型的，不同的牛奶保质期不同，一般情况下，牛奶分两类，一种是巴氏杀菌奶，保质期在半个月之内，而且必须冷藏，另一种是超高温杀菌奶，保质期6个月的都有，不过一般超市里卖的也就30天到45天左右。牛奶在人们的日常生活中是很常见的一种饮品。牛奶中含有丰富的营养物质，对人们的身体健康有很大的好处。并且牛奶容易消化吸收还十分的物美价廉，因此受到很受人们的欢迎和喜欢。牛奶是最理想的天然食品。牛奶中含有20多种氨基酸中有人体必须的8种氨基酸，因此能够有效的给人体补充营养物质。牛奶具有很多功效，喝牛奶的时间也决定了人体对于牛奶中营养物质的吸收程度。牛奶中还含有一些人体所需要的微量元素。牛奶中含有的锌元素，能够有效的加快人体的伤口愈合的速度，使人们早点康复，因此一些患者可以适当的喝一些牛奶，对于伤口愈合有很大的帮助。人们可以在睡觉之前喝一点牛奶，牛奶中含有的营养物质能够有效的促进人们的睡眠，从而达到美容养颜的效果。牛奶中含有的丰富蛋白质，维他命，矿物质等，具有很好的保湿功效，对人们的皮肤有很大的好处。选购新鲜的巴氏奶是非常重要的，一是看营养成分表：巴氏奶脂肪含量应不少于3.1g/100g，蛋白质含量不少于2.9g/100g。二是看外包装：巴氏奶通常标注“鲜牛乳”，三是看配料表：巴氏奶的配料只有生牛乳，四是看保质期：相较于常温奶，巴氏奶的保质期较短且需低温冷藏。我最近在喝每日鲜语，它确保每100毫升鲜奶含有3.6g优质蛋白和120mg原生高钙，营养丰富口感鲜醇，你也可以尝试一下。另外每日鲜语巴氏奶采用“原生锁鲜先进技术”，更多保留了牛奶中的营养成分。保质期为十五天购买后需要低温贮藏。1）纯牛奶超高温消毒、巴氏消毒和生鲜牛奶3种，消毒方式不同，保存条件不同，造成保质期长短不同2）超高温消毒奶的保质期一般在6—9个月3）巴氏消毒奶的保质期一般7—15天，最长不超过16天，且要求在2—6度下保存4）生鲜牛奶即新挤出的牛奶，未经杀菌处理的，一般在4度以下可保存24—36小时，最好是放在冰箱保鲜层内。千客网回答：一般酸奶的保质期是比牛初乳或鲜奶的保质期长7天左右。酸奶保质期一般在10天鲜奶3-5天一般普通的牛奶塑料袋装的30天，枕式硬纸袋的50天。鲜牛奶的保质期是48小时买后,鲜牛奶应该放置在2℃至6℃的冰箱里保存,不要让牛奶暴晒或照射灯光,日光、灯光均会破坏牛奶中的多种维生素。也不要把牛奶放在冰箱冷冻室中冷冻。包装上应该有，有的是2天，有的是7天。当天的新鲜牛奶（是从牛身上刚挤出来的那种，没经过任何加工的）是12小时，还得是在冷藏的情况下。当天新鲜的经过杀菌的牛奶是冷藏后24小时；百利包包装的加工纯牛奶是一个月，开启后冷藏为24小时；利乐枕包装的加工纯牛奶是45天，开启后冷藏是24小时；利乐砖（包），也有叫康美包的。一般是盒装的加工纯牛奶，保质期为6到7个月，开启后冷藏是24小时。牛奶分为两大类目前市场上的牛奶，大部分都属于杀菌乳，也就是我们常说的消毒奶。别看牛奶的包装上名称各异，什么“纯鲜牛奶”、“鲜牛奶”、“常温奶”，其实，从杀菌方法上来说，基本上就分两大类。一是巴氏杀菌乳，就是我们常见的“巴氏消毒奶”。顾名思义，就是采取“巴氏杀菌法”进行杀菌的牛奶。所谓“巴氏杀菌法”，就是在较长的时间内，用低温杀死牛奶中的致病菌，保留对人体有益的细菌。不过，由于这种方法不能消灭牛奶中所有的微生物，因此产品需要冷藏，保质期也比较短，一般只有几天，大家昵称为房子牛奶的鲜奶就属于此。另一种叫灭菌乳，是采用高温将牛奶中的细菌全部杀死。由于牛奶中一点微生物都不存在了，因此可在常温下保存，而且保质期比较长，一般可达3个月以上，大家昵称为袋装牛奶的纯奶就属于此。牛奶保质期短更新鲜，低温杀菌保留营养多！巴氏杀菌乳由于保存的营养成分较多，常被厂家叫做“鲜奶”。其实，杀菌时不管是低温还是高温，都会对牛奶的营养价值造成一定的影响，而真正的鲜奶应是没有经过加工的牛奶。在我们的市场里基本上没有生鲜牛奶，这种牛奶是未经杀菌的。巴氏消毒奶是规定时间内以不太高的温度处理液。一般都有两年。2个月。3个月以上。杀菌方式不同保质期不一样有一个月的，有6个月的。纯牛奶上是不添加任何添加剂的牛奶。如果是袋装或者瓶装密封的话，保质期能有一个月，要是散装的话，一天不喝就坏了。1.巴氏消毒奶是牛奶的初处理，在常温下仅仅能保存10天左右，一旦打开之后需要尽快食用，最好是在3天之内喝完。2.市场上有一种袋装的纯牛奶，经过一定的特殊处理，保质期较长一些，可保存45天左右。3.还有一种盒装的纯牛奶，这种牛奶主要用来长途运输，保存时间很长，可保存半年左右。奶袋上都有保质期的亲。60-180天一般还是早点喝比较好。当天的新鲜牛奶（是从牛身上刚挤出来的那种，没经过任何加工的）是12小时，还得是在冷藏的情况下。当天新鲜的经过杀菌的牛奶是冷藏后24小时；百利包包装的加工纯牛奶是一个月，开启后冷藏为24小时；利乐枕包装的加工纯牛奶是45天，开启后冷藏是24小时；利乐砖（包），也有叫康美包的。一般是盒装的加工纯牛奶，保质期为6到7个月，开启后冷藏是24小时。现在的牛奶都是经过加工，没加工的只有4-6个小时的保质期，加工后保质期长一点，有些需要冷藏保存的牛奶保质期就在一个礼拜左右，可以常温保存的牛奶最好不要超过1个月。一般是一个月。应该一个月。牛奶分为两大类目前市场上的牛奶，大部分都属于杀菌乳，也就是我们常说的消毒奶。别看牛奶的包装上名称各异，什么“纯鲜牛奶”、“鲜牛奶”、“常温奶”，其实，从杀菌方法上来说，基本上就分两大类。一是巴氏杀菌乳，就是我们常见的“巴氏消毒奶”。顾名思义，就是采取“巴氏杀菌法”进行杀菌的牛奶。所谓“巴氏杀菌法”，就是在较长的时间内，用低温杀死牛奶中的致病菌，保留对人体有益的细菌。不过，由于这种方法不能消灭牛奶中所有的微生物，因此产品需要冷藏，保质期也比较短，一般只有几天。另一种叫灭菌乳，是采用高温将牛奶中的细菌全部杀死。由于牛奶中一点微生物都不存在了，因此可在常温下保存，而且保质期比较长，一般可达3个月以上。低温杀菌保留营养多巴氏杀菌乳由于保存的营养成分较多，常被厂家叫做“鲜奶”。其实，杀菌时不管是低温还是高温，都会对牛奶的营养价值造成一定的影响，而真正的鲜奶应是没有经过加工的牛奶。加热对牛奶中营养影响最大的就是水溶性维生素和蛋白质。在加热过程中，大约有10%的B族维生素和25%的维生素C损失掉了，加热程度越深，这些营养损失得就越多。牛奶中有一种营养价值很高的乳清蛋白，在加热。一般好像都是三十天吧。三个月。牛奶之所以存在不同的保质期，是杀菌方式和包装方式不同决定的，与防腐剂没有关系；牛奶质量通常取决于高温灭菌时主要损失的维生素多少，蛋白质和钙的不受温度影响。牛奶杀菌主要有两种方法：巴氏杀菌法和超高温灭菌法。1、巴氏杀菌法利用较低的温度（一般在60℃~85℃），就可以杀死致病菌，保存牛奶中的风味物质，是一种损失较少的热杀菌消毒法。采用这种杀菌方法的牛奶被称为巴氏奶或低温奶，保质期一般为2~7天，需要冷链运输，冷藏保存。2、超高温灭菌法是把牛奶瞬间加热到135℃~150℃，持续2~6秒，几乎能杀灭全部细菌，保质期达到6个月以上，而且可以常温储存，因此又叫常温奶。扩展资料牛奶挑选的技巧1、挑选牛奶时，先去冰柜上选择营养价值保存最好的巴氏消毒奶。当然为了携带储存方便也可以选用普通的常温奶。2、牛奶的配料表中可以查看营养成分，蛋白质、脂肪、乳固体的含量高的话代表牛奶的质量比较好。3、用力摇牛奶后迅速倒入透明玻璃杯，再慢慢倒出来，观察玻璃杯壁的奶膜是否均匀，成膜均匀代表牛奶品质好，如果有小的沉淀物说明奶源可能受污染，细菌超标。4、把牛奶加热到六七十度，拿出来倒在杯子中，奶源品质好的牛奶会在表面形成一。你好，牛奶保质期的长短主要取决于牛奶的杀菌工艺，目前市面上一般就两种奶，巴氏奶和常温奶。巴氏奶是巴氏灭菌奶，是指将奶加热到75-90℃，保温15-16秒的杀菌，瞬间杀死致病微生物，属非无菌灌装，但其细菌含量不会对健康造成威胁。但保质期有要求，最好在3天以内，对储存条件有要求，一般为2℃～6℃。常温奶，是超高温灭菌奶，是指在130℃～140℃下，进行4～15秒的瞬间灭菌处理，完全破坏其中可生长的微生物和芽孢，并在无菌状态下灌装。这种保质期通常可达6个月～9个月，甚至更长时间，可在常温下保存。希望我的回答对你有所帮助。保质期越短的越早喝越好，里面几乎没添加什么防腐剂，保质期一年的就防腐添加剂加得多一点，质量应该没问题的。里面加的防腐剂成分不一样保质期越短的牛奶越好、。"""
		sentences = self.__split_sentences(text_data)
		sentences = self.__filter_by_keywords(sentences)					# 第一次过滤  关键词过滤。重新赋给 sentences
		sentences = self.__filter_by_vsm(sentences)							# 第二次过滤  使用 VMS 算法过滤(其实还是 TF-IDF vsm 句子相似度计算) 注意，返回后的每个句子的 words 已经同一化，可能与原句子成分不同，但语义相同。
		pass																# 根据相似度阀值，决定最后的答案抽取返回内容
		res_sentences = self.__answer_extract(sentences)

		# test
		# for sentence in res_sentences:
		# 	print(sentence['text'],'score:',sentence['score'],end=' ')
		# 	print()
		#
		pass


	def ask_me(self,query_text):
		self.__query_text = query_text
		# 从数据库搜索答案
		res_sentence = self.__get_answer_from_database()
		if res_sentence is not None :								
			return res_sentence												# 从数据库找到了相似问题的答案，直接返回答案，不需要在开放域进行查找
		# 从 web 语料库搜索答案
		res_sentence = self.__get_answer_from_web()

		return res_sentence


if __name__ == '__main__':
	tf_idf = Tf_idf()
	res = tf_idf.ask_me("汶川地震多少级？")										# 现在返回的是 根据语料文本返回指定查询句子的最佳匹配，最相似的句子。

	pass
