# -*- coding:utf-8 -*-

import os
import re
import sys
from xml.dom.minidom import parse

'''
20250911
脚本功能：
用来提取Java项目中的路由（目前支持Servlet、Spring项目、Struts2项目）
｜
已知问题（影响不大）：
在匹配如："@WebServlet({"/hello", "/hi"})" 这样的多个路径映射注解时，最终得到的是："/hello        其它参数:/hi"
'''


def isConfigClass(file_content):
    string_array = ["@Configuration", "@ComponentScan", "@Import", "@PropertySource", "@EnableAutoConfiguration"]
    for str in string_array:
        if str in file_content:
            return True
    return False


def routeClean(route):
    route = route.replace('\n', '').replace(' ', '').replace('	', '')
    route = route.replace('value=', '').replace('path=', '').replace('urlPatterns=', '')
    route = route.replace('{', '').replace('}', '').replace('"', '')
    if not route.startswith("/"):
        route = "/" + route
    route = re.sub(r'name=.*?,', '', route, 1)
    route = re.sub(',', '       其它参数:', route, 1)

    while "//" in route:
        route = route.replace('//', '/')
    return route


# 遍历指定文件夹中所有的文件，返回所有符合后缀条件文件的绝对路径列表
def recursive_listdir(path_0, suffix):
    files = os.listdir(path_0)
    for file in files:
        file_path = os.path.join(path_0, file)
        if os.path.isfile(file_path):
            if (path_0 + '/' + file).endswith(suffix):
                yield path_0 + '/' + file
        elif os.path.isdir(file_path):
            yield from recursive_listdir(file_path, suffix)


def searchRoute(path_list):
    print(
        '\n\nSpring注解型路由搜索-开始\n|\n-------@RequestMapping注解中的参数解释:\nvalue/path/空:请求URL路径\nmethod:指定请求方式\nparams:指定请求参数\nheaders:指定请求头\nconsumes'
        ':指定请求内容类型\nproduces:指定响应数据类型')
    print(
        '-------@WebServlet注解中的参数解释:\nvalue/urlPatterns/空:指定Servlet的访问路径\nname:指定Servlet名称,'
        '默认类名(该参数可忽略)\nloadOnStartup:Servlet启动顺序,值越小启动越早\ninitParams:初始化参数\nasyncSupported:Servlet是否支持异步处理请求,默认为false')
    for i, file_path in enumerate(path_list):
        with open(file_path, "r", errors='ignore') as f:
            file_content = f.read()
        tmp = os.path.getsize(file_path)
        # 将文件大小转换为KB单位
        size = float('%.1f' % float(tmp / 1000))
        pattern_servlet = re.compile(r'@WebServlet\((.*?)\).{,1000}public\s{1,10}class', re.DOTALL)
        result_servlet = pattern_servlet.findall(file_content)
        if result_servlet:
            print('\n共计数量:{};正在扫描第{}个文件[{}KB]: {}'.format(len(path_list), i, size, file_path.replace(path, "")))
            for route in result_servlet:
                route = routeClean(route)
                print(route)

        else:
            '''
            1、匹配Class头上的 @RequestMapping 注解，如：
                @Controller
                @RequestMapping(value = "/admin")
                public class LoginControl {
            '''
            pattern = re.compile(r'@RequestMapping\((.*?)\).{,1000}public\s{1,10}class', re.DOTALL)
            result = pattern.findall(file_content)  # 提取正则匹配的内容,多行模式（匹配换行）
            if result:
                print('\n[自动拼接]\n共计数量:{};正在扫描第{}个文件[{}KB]: {}'.format(len(path_list), i, size,
                                                                      file_path.replace(path, "")))
                class_route = result[0]
                pattern2 = re.compile(
                    r'@(?:RequestMapping|PostMapping|GetMapping|PutMapping|DeleteMapping|PatchMapping)\((.*?)\)',
                    re.DOTALL)
                result2 = pattern2.findall(file_content)
                if result2:
                    j = 1
                    while j < len(result2):
                        route = (routeClean(class_route + '/' + result2[j]))
                        print(route)
                        j += 1
                else:
                    print("当前只在Class上找到注解, 未在方法上找到, 可忽略.")
            else:
                pattern2 = re.compile(
                    r'@(?:RequestMapping|PostMapping|GetMapping|PutMapping|DeleteMapping|PatchMapping)\((.*?)\)',
                    re.DOTALL)
                result2 = pattern2.findall(file_content)
                if result2:
                    print('\n共计数量:{};正在扫描第{}个文件[{}KB]: {}'.format(len(path_list), i, size, file_path.replace(path, "")))
                    for route in result2:
                        route = routeClean(route)
                        print(route)
                else:
                    pass
    print("|\nSpring注解型路由搜索-结束")


def searchOtherRoute(path_list):
    print('\n\n动态路由搜索-开始\n|')
    for i, file_path in enumerate(path_list):
        with open(file_path, "r", errors='ignore') as f:
            file_content = f.read()
        tmp = os.path.getsize(file_path)
        size = float('%.1f' % float(tmp / 1000))
        '''
        ServletRegistration 中的 addMapping方法: 动态添加路由
        ServletContext.class 中的 addServlet方法: 动态添加路由
        ViewControllerRegistry 中的 addViewControllers方法:添加视图控制器(如将 /WEB-INF/jsp/login.jsp 与 /login 作绑定)
        RequestMappingHandlerMapping 中的 registerMapping
        SimpleUrlHandlerMapping 中的 registerHandler 
        addResourceHandler:指定静态资源的访问路径(通过转换访问到一些不能直接访问的文件)
        '''
        pattern_servlet = re.compile(
            r'(\.(?:addMapping|addServlet|addViewControllers|registerMapping|registerHandler|addResourceHandler)\(.*?\))',
            re.DOTALL)
        result_servlet = pattern_servlet.findall(file_content)
        if result_servlet:
            print('共计数量:{};正在扫描第{}个文件[{}KB]: {}'.format(len(path_list), i, size,
                                                        file_path.replace(path, "")))
            for tmp in result_servlet:
                print(tmp)
    print('|\n动态路由搜索-结束\n\n')


def main_web_xml(dom_tree):
    root = dom_tree.documentElement
    print("------------------------------1、项目名称及描述------------------------------")
    getDomContent(root, "display-name")
    getDomContent(root, "description")
    print("------------------------------2、访问域名时默认页面，从上到下寻找------------------------------")
    getWelcome(root)
    print(
        "------------------------------3、配置项目环境参数，在web应用程序的所有servlet和JSP页面中使用------------------------------")
    getContextParam(root)
    print("------------------------------4、监听器------------------------------")
    getListener(root)
    print("------------------------------5、过滤器------------------------------")
    getFilter(root)
    print("------------------------------6、路由------------------------------")
    getServlet(root)


def getDomContent(root, tag_name):
    tag_name_list = root.getElementsByTagName(tag_name)
    if tag_name_list:
        name = tag_name_list[0].firstChild.data.strip()
        print(getExplainInfo(tag_name, name))
    else:
        print("不存在" + tag_name + "节点")


def getExplainInfo(name, value):
    explain_info = ""
    if name == "display-name":
        explain_info = "[{}]: {}  # 项目名称(非必要)".format(name, value)
    elif name == "description":
        explain_info = "[{}]: {}  # 项目描述(非必要)".format(name, value)
    else:
        explain_info = "[{}]: {}".format(name, value)

    return explain_info


def getWelcome(root):
    tag = root.getElementsByTagName("welcome-file-list")
    if tag:
        for tag2 in tag:
            welcome_file = tag2.getElementsByTagName("welcome-file")
            if welcome_file:
                for tag3 in welcome_file:
                    print("[主页默认页面]: " + tag3.firstChild.data.strip())


def getContextParam(root):
    tag = root.getElementsByTagName("context-param")
    if tag:
        try:
            for tag2 in tag:
                param_name = tag2.getElementsByTagName("param-name")[0].firstChild.data.strip()
                param_value = tag2.getElementsByTagName("param-value")[0].firstChild.data.strip()
                print('[context-param]: {"' + param_name + '":"' + param_value + '"}')
        except AttributeError as e:
            print(e)


def getListener(root):
    tag = root.getElementsByTagName("listener")
    if tag:
        for tag2 in tag:
            listener_class = tag2.getElementsByTagName("listener-class")[0].firstChild.data.strip()
            print("[listener-class]: " + getClassInfo(listener_class))


# <filter><filter-name>test123</filter-name></filter>
# <filter><filter-name>test456</filter-name></filter>
def getFilter(root):
    tag_filter = root.getElementsByTagName("filter")
    tag_filter_mapping = root.getElementsByTagName("filter-mapping")
    for i, tag in enumerate(tag_filter):
        i += 1
        # 获取<filter-name>标签的值
        filter_name_value = tag.getElementsByTagName("filter-name")[0].firstChild.data.strip()
        # 获取<filter-class>标签的值
        filter_class_value = tag.getElementsByTagName("filter-class")[0].firstChild.data.strip()
        filter_class_value = getClassInfo(filter_class_value)
        j = 0
        for tag2 in tag_filter_mapping:
            # 获取<filter-name>标签的值
            name = tag2.getElementsByTagName("filter-name")[0].childNodes[0].data.strip()
            if name == filter_name_value:
                try:
                    # 获取<url-pattern>标签的值
                    url = tag2.getElementsByTagName("url-pattern")[0].childNodes[0].data.strip()
                    if j == 0:
                        print("---------------------\n---------------------")
                        print("第" + str(i) + "组  " + getExplainInfo("filter-name", filter_name_value))
                        print("第" + str(i) + "组 " + getExplainInfo("filter-class", filter_class_value))
                        j = 999
                    print("第" + str(i) + "组  " + getExplainInfo("url-pattern", url))
                except IndexError as e:
                    print(e)
            # 如果该filter为最后一个元素，且还未找到对应的filter-mapping则进入
            elif tag2 == tag_filter_mapping[-1] and (j == 0):
                print("---------------------\n---------------------")
                print("第" + str(i) + "组  " + getExplainInfo("filter-name", filter_name_value))
                print("第" + str(i) + "组 " + getExplainInfo("filter-class", filter_class_value))
                print("第" + str(i) + "组  " + getExplainInfo("url-pattern", "未找到对应路由(可能原因: 路由被注释)"))
        tag_init_param = tag.getElementsByTagName("init-param")
        # 判断是否存在该节点
        if tag_init_param:
            string = ''
            try:
                for param in tag_init_param:
                    name = param.getElementsByTagName("param-name")[0].firstChild.data.strip()
                    value = param.getElementsByTagName("param-value")[0].firstChild.data.strip()
                    string += '"{}":"{}", '.format(name, value)
                print("第" + str(i) + "组      [初始参数]: {" + string[:-2] + "}")
            except AttributeError as e:
                print(e)
            except IndexError as e:
                print(e)


def getServlet(root):
    tag_servlet = root.getElementsByTagName("servlet")
    tag_servlet_mapping = root.getElementsByTagName("servlet-mapping")
    if tag_servlet:  # 判断是否存在该节点
        for i, tag in enumerate(tag_servlet):
            i += 1
            # 获取<servlet>中的<servlet-name>标签的值
            servlet_name_value = tag.getElementsByTagName("servlet-name")[0].firstChild.data.strip()
            # 获取<servlet>中的<servlet-class>标签的值
            servlet_class_value = tag.getElementsByTagName("servlet-class")[0].firstChild.data.strip()
            servlet_class_value = getClassInfo(servlet_class_value)
            j = 0
            for tag2 in tag_servlet_mapping:
                # 获取<servlet-mapping>中的<servlet-name>标签的值
                name = tag2.getElementsByTagName("servlet-name")[0].childNodes[0].data.strip()
                if name == servlet_name_value:
                    # 获取<servlet-mapping>中的<url-pattern>标签的值
                    url = tag2.getElementsByTagName("url-pattern")[0].childNodes[0].data.strip()
                    if j == 0:
                        print("---------------------\n---------------------")
                        print("第" + str(i) + "组  [servlet-name]: " + servlet_name_value)
                        print("第" + str(i) + "组 [servlet-class]: " + servlet_class_value)
                        j = 999
                    print("第" + str(i) + "组   [url-pattern]: " + url)
                    # 如果该filter为最后一个元素，且还未找到对应的filter-mapping则进入
                elif tag2 == tag_servlet_mapping[-1] and (j == 0):
                    print("---------------------\n---------------------")
                    print("第" + str(i) + "组  [servlet-name]: " + servlet_name_value)
                    print("第" + str(i) + "组 [servlet-class]: " + servlet_class_value)
                    print("第" + str(i) + "组   [url-pattern]: 未找到对应路由(可能原因: 路由被注释)")
            tag_init_param = tag.getElementsByTagName("init-param")
            # 判断是否存在该节点
            if tag_init_param:
                string = ''
                try:
                    for param in tag_init_param:
                        name = param.getElementsByTagName("param-name")[0].firstChild.data.strip()
                        value = param.getElementsByTagName("param-value")[0].firstChild.data.strip()
                        string += '"{}":"{}", '.format(name, value)
                    print("第" + str(i) + "组       [初始参数]: {" + string[:-2] + "}")
                except AttributeError as e:
                    print(e)


# 对于特殊作用的类名，进行解释说明，返回解释后的字符串
def getClassInfo(class_name):
    if class_name == "org.springframework.web.servlet.DispatcherServlet":
        class_name += "  #SpringMVC核心控制器，负责将请求转发给相应的Controller处理，请关注其配置文件（来自：spring-webmvc-5.2.5.RELEASE.jar）"
    elif class_name == "org.springframework.web.filter.CharacterEncodingFilter":
        class_name += "  #设置字符编码，一般用于处理中文乱码问题，可忽略（来自：spring-web.jar）"
    elif class_name == "org.springframework.web.context.ContextLoaderListener":
        class_name += "  #用于在web应用启动时，自动加载Spring配置文件并初始化Spring容器（来自：spring-web.jar）"
    elif class_name == "org.springframework.web.util.IntrospectorCleanupListener":
        class_name += "  #用于在应用程序停止时清理BeanUtils缓存（来自：spring-web.jar）"
    elif class_name == "org.apache.axis.transport.http.AxisHTTPSessionListener":
        class_name += "  #用于在Web应用程序启动时初始化Axis，并在Web应用程序关闭时清理Axis（来自：axis-1.4.jar）"
    elif class_name == "org.springframework.security.web.session.HttpSessionEventPublisher":
        class_name += "  #监听HttpSession的创建和销毁事件，从而更好的管理session（来自：spring-security-web.jar）"
    elif class_name == "org.springframework.web.filter.DelegatingFilterProxy":
        class_name += "  #将一个Filter交由Spring容器管理，从而实现Filter的依赖注入，作用是拦截请求（来自：spring-web.jar）"
    elif class_name == "org.springframework.orm.hibernate5.support.OpenSessionInViewFilter":
        class_name += "  #过滤器，其作用是在整个请求处理过程中保持会话持久化，从而实现持久化管理（来自：spring-orm.jar）"
    elif class_name == "com.alibaba.druid.support.http.StatViewServlet":
        class_name += "  #提供druid的监控统计功能（可能存在默认口令或未授权访问情况）（来自：druid-1.1.16.jar）"
    elif class_name == "org.springframework.web.context.request.RequestContextListener":
        class_name += "  #为每个请求创建一个RequestContext对象，以便于在程序中获取到当前请求的上下文，从而获取到请求的参数、属性等（来自：spring-web-4.3.4.RELEASE.jar）"
    elif class_name == "org.springframework.web.util.Log4jConfigListener":
        class_name += "  #监听web.xml中配置的log4j配置文件，并且能够在服务器启动时自动加载log4j配置文件（来自：spring-web-4.3.4.RELEASE.jar）"
    elif class_name == "com.alibaba.druid.support.http.WebStatFilter":
        class_name += "  #收集Web应用统计数据，如Session数量、访问页面数量等，可在druid监控页面查看（来自：druid-1.1.16.jar）"
    elif class_name == "com.common.logging.Log4jInit":
        class_name += "  #初始化Log4j，使得web应用可以使用Log4j日志记录系统（来自：log4j-1.2.17.jar）"
    elif class_name == "org.springframework.session.web.http.CTPDelegatingFilterProxy":
        class_name += "  #用于支持HTTP会话的管理，从而替代HttpSession的实现（来自：spring-session-core-xxx.jar）"
    elif class_name == "org.springframework.orm.hibernate4.support.OpenSessionInViewFilter":
        class_name += "  #作用是在整个请求完成之后，才关闭Session（来自：spring-orm.jar）"
    elif class_name == "org.apache.axis.transport.http.AxisServlet":
        class_name += "  #作用是支持WebService（来自：axis.jar）"
    elif class_name == "org.apache.shiro.web.servlet.ShiroFilter":
        class_name += "  #Shiro配置的过滤器，需重点查看"
    elif class_name == "com.jfinal.core.JFinalFilter":
        class_name += "  #这是一个JFinalFilter框架的项目，JFinalFilter来接收所有的请求"
    elif class_name == "org.springframework.orm.hibernate3.support.OpenSessionInViewFilter":
        class_name += "  #提高了数据库访问的性能(来自:spring-orm-x.y.z.jar)"
    elif class_name == "javax.faces.webapp.FacesServlet":
        class_name += "  #该路由可能存在Faces反序列化漏洞"
    elif class_name == "com.caucho.hessian.server.HessianServlet":
        class_name += "  #该路由可能存在Hessian反序列化漏洞"
    elif class_name == "xxx":
        class_name += "  #xxx"
    return class_name


def main_struts_xml(dom_tree):
    global bean_list
    # 获取所有constant节点
    constants = dom_tree.getElementsByTagName("constant")
    # 遍历并查找 name="struts.enable.DynamicMethodInvocation"
    for node in constants:
        if node.getAttribute("name") == "struts.enable.DynamicMethodInvocation":
            value = node.getAttribute("value")
            if value == "true":
                print("允许通配符动态方法调用")
            else:
                print("禁止通配符动态方法调用")
        elif node.getAttribute("name") == "struts.devMode":
            value = node.getAttribute("value")
            if value == "true":
                print("开发者模式: 开启")
            else:
                print("开发者模式: 关闭")
        elif node.getAttribute("name") == "struts.action.extension":
            global extension
            extension = "." + node.getAttribute("value")
            print(f"struts2请求URL自定义后缀(可配置多个用逗号分隔,若包含空项,则支持无后缀访问): {extension}")
        elif node.getAttribute("name") == "struts.configuration.xml.reload":
            value = node.getAttribute("value")
            if value == "true":
                print("struts.xml等配置文件热重载: 开启")
            else:
                print("struts.xml等配置文件热重载: 关闭")
        elif node.getAttribute("name") == "struts.enable.SlashesInActionNames":
            value = node.getAttribute("value")
            if value == "true":
                print("Action名包含斜杠/,便于[伪REST风格]或分层路径的Action映射(如:user/profile.html): 开启")
            else:
                print("Action名包含斜杠/,便于[伪REST风格]或分层路径的Action映射(如:user/profile.html): 关闭")
        elif node.getAttribute("name") == "struts.ui.theme":
            value = node.getAttribute("value")
            print(f"UI主题: {value}")
        elif node.getAttribute("name") == "struts.objectFactory":
            value = node.getAttribute("value")
            print(f"指定对象工厂为{value}: Action/拦截器等由Spring容器创建并可注入依赖,实现Struts2与Spring集成.")
        elif node.getAttribute("name") == "struts.multipart.maxSize":
            value = node.getAttribute("value")
            print(f"上传文件大小上限 {value} 字节")
        elif node.getAttribute("name") == "xxx":
            value = node.getAttribute("value")
            if value == "true":
                print("xxx")
            else:
                print("xxx")

    actions = dom_tree.getElementsByTagName("action")
    for action in actions:
        namespace = ""
        fa = action.parentNode
        # 判断action的父节点是否为package
        if fa.tagName == "package":
            namespace = fa.getAttribute("namespace")

        # 将bean的id属性与action的class属性做关联,找到对应的类文件名称
        class_1 = action.getAttribute("class")
        # print(class_1)
        if class_1 in bean_list:
            class_1 = bean_list[class_1]
            # print(class_1)
        print("-类文件 " + class_1 + " 中, 路由与方法对应关系:")

        method = action.getAttribute("method")
        name = action.getAttribute("name")
        result = namespace + "/" + name + extension.split(",")[0]
        if method in ("", "execute"):
            print(result + "  -->  " + "execute()")
        elif method == "{1}":
            # 将name中第一个*号替换为任意公共方法名
            result = namespace + "/" + re.sub("\*", "任意公共方法名", name, count=1) + extension.split(",")[0]
            print(result + "  -->  " + "任意公共方法()")
            # print(action.getAttribute("method"))
        else:
            print(result + "  -->  " + method)
        # exit("123")
        if len(action.getElementsByTagName("result")) != 0 and action.getElementsByTagName("result")[0].getAttribute(
                "name") != "":
            print("|\n--视图映射关系如下(方法返回特定字符串时,返回相应路径下的视图文件):")
            for tag in action.getElementsByTagName("result"):
                print("  " + tag.getAttribute("name") + "  -->  " + tag.firstChild.data.strip())
        print("\n")


if __name__ == "__main__":
    global extension
    extension = ""  # struts2路由自定义后缀,默认空
    global bean_list
    bean_list = {}
    try:
        path = sys.argv[1]  # 从外面接收第一个参数
    except IndexError:
        exit("末指定代码路径")
    try:
        web_xml_list = list(recursive_listdir(path, 'WEB-INF/web.xml'))
        if web_xml_list:
            web_xml = web_xml_list[0]
            print("web.xml 配置文件解析如下:\n配置文件: " + web_xml)
            # 打开XML文件并解析为DOM对象
            dom_tree_1 = parse(web_xml)
            main_web_xml(dom_tree_1)
        else:
            print('未搜索到web.xml文件.')
        print("\n\n\n")
        struts_xml_list = list(recursive_listdir(path, 'struts.xml'))
        if struts_xml_list:
            struts_xml = struts_xml_list[0]
            print(f"Struts2 配置文件解析如下:\n配置文件[1]: {struts_xml}")
            # 打开XML文件并解析为DOM对象
            dom_tree_2 = parse(struts_xml)
            if len(dom_tree_2.getElementsByTagName("struts")) != 0:
                main_struts_xml(dom_tree_2)
            # 获取所有的xml文件路径
            xml_filepath_list = list(recursive_listdir(path, ".xml"))

            # 遍历所有xml配置文件中的bean名称以及对应class名称
            for xml_filepath in xml_filepath_list:
                try:
                    # 打开XML文件并解析为DOM对象
                    dom_tree_3 = parse(xml_filepath)
                    if len(dom_tree_3.getElementsByTagName("beans")) != 0:
                        beans = dom_tree_3.getElementsByTagName("bean")
                        for bean in beans:
                            id_0 = bean.getAttribute("id")
                            class_0 = bean.getAttribute("class")
                            bean_list[id_0] = class_0
                except Exception as e:
                    print(f"文件解析失败,可忽略.({xml_filepath})")

            xi = 2
            for xml_filepath in xml_filepath_list:
                if xml_filepath.endswith("struts.xml"):
                    continue
                try:
                    # 打开XML文件并解析为DOM对象
                    dom_tree_4 = parse(xml_filepath)
                    if len(dom_tree_4.getElementsByTagName("struts")) != 0:
                        print(f"\n配置文件[{xi}]: " + xml_filepath)
                        main_struts_xml(dom_tree_4)
                        xi += 1
                except Exception as e:
                    print(f"文件解析失败,可忽略.({xml_filepath})")
        else:
            print('未搜索到struts.xml文件.')
        # 获取所有的java文件路径
        java_filepath_list = list(recursive_listdir(path, ".java"))
    except FileNotFoundError as e:
        print("文件不存在.")
        exit(e)
    searchRoute(java_filepath_list)
    searchOtherRoute(java_filepath_list)
