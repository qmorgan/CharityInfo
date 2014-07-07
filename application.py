import os, datetime, re, glob,sys
from flask import Flask, request, redirect, url_for, render_template, redirect, url_for, flash
from werkzeug import secure_filename
# from flask_sqlalchemy import SQLAlchemy
from flask.ext.sqlalchemy import SQLAlchemy
import sqlite3
from os.path import exists
import codecs
from sqlalchemy import exc
from sqlalchemy import event
from sqlalchemy.pool import Pool

basedir = os.path.abspath(os.path.dirname(__file__))

application = Flask(__name__) #update 
app = application
app.debug = True

try:
    import os
    import sys
    if not os.environ.has_key("MYSQL_PASS"):
        print "You need to set the environment variable MYSQL_PASS to"
        print "point to your mysql password"
        sys.exit(1)
    elif not os.environ.has_key("RDS_HOST"):
        print "You need to set the environment variable RDS_HOST to"
        print "point to your amazon RDS host" 
    else: 
        passwd = os.environ.get("MYSQL_PASS")
        rdshost=os.environ.get("RDS_HOST")
    
    # local
    # db_path = 'mysql://root:'+passwd+'@localhost/cnavigator'
    # aws
    db_path = 'mysql://qmorgan:'+passwd+'@'+rdshost+'/cnavigator'

    app.config['SQLALCHEMY_DATABASE_URI'] = db_path
    db = SQLAlchemy(app)

    app.config.from_object(__name__)
    


    # create engine for feeding SQL
    # http://docs.sqlalchemy.org/en/rel_0_9/core/connections.html
    eng = db.create_engine(db_path, pool_size=20, pool_recycle=3600)
    conn=eng.connect()

    # db.create_all()
    # db.create_all()

    
except:
    print "Cannot connect!"





# this doesn't seem to work.. 
@event.listens_for(Pool, "checkout")
def ping_connection(dbapi_connection, connection_record, connection_proxy):
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("SELECT 1")
    except:
        # optional - dispose the whole pool
        # instead of invalidating one at a time
        # connection_proxy._pool.dispose()

        # raise DisconnectionError - pool will try
        # connecting again up to three times before raising.
        raise exc.DisconnectionError()
    cursor.close()

@app.route("/")
def index():
    # right now just force them to go to search
    try:
        passwd = os.environ.get("MYSQL_PASS")
    except:
        passwd = "Unknown"
    # return passwd
    return redirect(url_for('search'))


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


@app.route("/search", methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        query = request.form['query']
        if query not in (""," ",None):
            try:
                # try to search
                count = 0
                countlimit=20
                
                results = search_parse(query,countlimit=countlimit)
                print 'search done'
                totalcount = int(results.rowcount)
                print 'Found %i items' % (totalcount)
                result_txt = "<ul style='padding-left: 0px;'>"

                
                # loop through results and post box
                for result in results:
                    count += 1
                    if count >= countlimit: # only print the first 30
                        break
                    
                    mycharityname = str(result['NAME']).title()
                    myshortcharityname = mycharityname
                    if len(mycharityname) > 28:
                        myshortcharityname = ' '.join(mycharityname[0:28].split(' ')[0:-1])+' ...'
                    result_txt += '''
                    <header class="bridgetitle" id="charityname" style="padding-top:0px;padding-bottom:0px;">{c_name}</header>
                    '''.format(c_name = mycharityname)
                    
                    predicted_score = result['CN_SCORE_PREDICT']
                    
                    cn_rating_exists = False
                    cn_id = -1
                    ein=result['EIN']
                    
                    # donor advisory: -1 if not known, CN_ID if found.
                    cndonoradvisoryid = check_for_donor_advisory(ein)
                    
                    cnres = check_for_CN_rating(ein)
                    for res in cnres:
                        cn_id=res['CN_ID']
                        cn_rating = res['OVERALL_VALUE']
                        cn_rating_str = "{} / 70".format(cn_rating)
                        cn_rating_link = "http://www.charitynavigator.org/index.cfm?bay=search.summary&orgid={}".format(cn_id)
                        c_value = "<a href={}>{}</a>".format(cn_rating_link,cn_rating_str)
                        # change predicted score to out-of-bag estimate so it is not biased
                        predicted_score = res['OOB_SCORE']
                    if cn_id == -1:
                        if cndonoradvisoryid == -1:
                            cn_rating_str = "Not Available"
                            cn_rating_link = "http://www.charitynavigator.org/index.cfm?bay=search.profile&ein={}".format(ein)
                            c_value = "<a href={}>{}</a>".format(cn_rating_link,cn_rating_str)
                        else: 
                            cn_rating_str = "DONOR ADVISORY"
                            cn_rating_link = "http://www.charitynavigator.org/index.cfm?bay=search.summary&orgid={}".format(cndonoradvisoryid)
                            c_value = "<a href={}>{}</a>".format(cn_rating_link,cn_rating_str)

                    
                    categoryres = get_category(ein)
                    c_class = 'UNKNOWN'
                    for res in categoryres:
                        c_class = res['NTEECAT12']
                    
                
                    c_class_str = translate_nteecode(c_class)
                    
                    percentile = 0.0
                    percentile = get_percentile(c_class,predicted_score)
                    
                    donationlink="https://www.networkforgood.org/donation/MakeDonation.aspx?ORGID2={}".format(ein)
                    
                    colorstr = "#8c92ac"
                    colorstr2 = "#8c92ac"
                    result_txt += """
                                <!-- set data-interval= an integer to auto-slide after initial click -->
                                <div id="Carousel-{res_num}" class="carousel slide" data-interval="false"> 
                                   <!-- Carousel indicators -->
                                   <ol class="carousel-indicators">
                                      <li data-target="#Carousel-{res_num}" data-slide-to="0" class="active"></li>
                                      <li data-target="#Carousel-{res_num}" data-slide-to="1"></li>
                                      <li data-target="#Carousel-{res_num}" data-slide-to="2"></li>
                                   </ol>
                                   <!-- Carousel items -->
                                   <div class="carousel-inner">
                                   """.format(res_num=count)
                                   
                    minxpos=72
                    maxxpos=520
                    xloc = predicted_score/70.0*(maxxpos-minxpos)+ minxpos
                    result_txt += """ <div class="item active">
                                          <div id="charitypictures">

                                            <li>""" 
                    result_txt += """       <p> <b>Class:</b> {c_class} </p>""".format(c_class=c_class_str)
                    if cndonoradvisoryid == -1:
                        SummaryText = """       This charity is predicted to be ranked higher than 
                                            <i style="color:#E7573C;">{perc:.1f}%
                                            </i> of the charities in its class.
                                            """.format(colorstr2 = '#888888',perc=percentile)
                    else:
                        SummaryText = """ This charity has a {} on  
                                        CharityNavigator.org. See their site for details.""".format(c_value)
                    result_txt += """       <h3 style="
                                                margin-left:30px;
                                                margin-right:30px;
                                                text-align:center;
                                                border:1px solid #E7573C;
                                                "> {}
                                            </h3>""".format(SummaryText)
                    
                    result_txt += """       <p  style="
                                                margin-top: 20px;
                                                margin-bottom: 0px;
                                                "> 
                                                Predicted CharityNavigator.org Rating: {c_predict:.2f} / 70
                                            </p>""".format(c_predict=predicted_score)
                    result_txt += """       <p style="
                                                color:{colorstr2};
                                                margin-bottom:0px;
                                                "> 
                                                <i>Actual CharityNavigator.org Rating: {c_value} </i>
                                            </p>""".format(colorstr2 = '#888888',c_value=c_value)
                    result_txt += """          
                                            </li>"""
                    result_txt += """       <img src="http://qmorgan.dyndns.org/charityverity/{c_val}.png" width="580px" style="position:absolute;z-index:-1"></img>""".format(c_val=c_class)
                    

                    
                    svg_label = """
                    <line x1="{xloc:.2f}" y1="32" x2="{xloc2:.2f}" y2="280" stroke="black" stroke-width="30" stroke-opacity="0.8"></line>
                    <polygon points="{xloc_minus},280 {xloc_plus},280 {xloc},308 " style="fill:black;stroke:white;stroke-width:0;fill-opacity:0.8"></polygon>
                    """.format(xloc=xloc, xloc2=xloc, xloc_minus=xloc-15, xloc_plus=xloc+15)
                         
                    # add to legend
                    # svg_label += """
                    # <line x1="83" x2="110" y1="90" y2="90" stroke="black" stroke-width="1"></line>
                    # <text text-anchor="start" x="120" y="95" font-size="13">{title}</text>
                    # """.format(title=mycharityname)
                    
                    svg_label += """
                    <text text-anchor="start" x="0" y="0" fill="white" transform="translate({xstart},280)rotate(-90)">{title}</text>
                    
                    """.format(xstart=xloc+4,title=myshortcharityname)
                    
                    linemarker = ""
                    
                    linemarker_1 = """
                    <line x1="{xloc:.2f}" y1="32" x2="{xloc2:.2f}" y2="310" stroke="teal" stroke-width="2" />
                    """.format(xloc=xloc,xloc2=xloc)
                    
                    # alternative. old
                    svg_label_1 = """
                    <text text-anchor="end" x="{maxxpos}" y="25">{title}</text>
                    <line x1="{xstart}" x2="{maxxpos}" y1="32" y2="32" stroke="teal" stroke-width="2"></line>
                    """.format(xstart=xloc-30, maxxpos=maxxpos,title=mycharityname)
                    
                    
                    # alternative. Old. 
                    svg_label_2 = """
                    <text text-anchor="end" x="195" y="184">This Charity</text>
                    <line x1="200" x2="{xloc3:.2f}" y1="180" y2="180" stroke="teal" stroke-width="2"></line></svg>
                    """.format(xloc3=xloc)
                    
                    result_txt += """          <svg width="580" height="464">
                                                {linemarker}
                                                {svglabel}
                                            </svg>""".format(linemarker=linemarker,svglabel=svg_label)
                                        
                    result_txt += """    </div><!-- end charity pictures -->
                                        <div class="carousel-caption">Overview
                                        </div>
                                      </div>
                                     """
                                            #.format(c_class = str(result['CHARITYCLASS']),
                                            #    colorstr = colorstr, c_predict=result['OOB_SCORE'],
                                            #    c_value = str(result['OVERALL_VALUE']),colorstr2 = '#cccccc')#,
                                     # <p> This is higher than <b>XX.X%</b> of all ranked charities of its class</p> 
                                     
                    result_txt += """<div class="item">
                                            <div id="charitypictures">
                                            
                                             <p style="text-align:center;padding:8px"> <b>Mission</b></p>
                                             
                                            {description}
                                            <p style="text-align:center;padding-top:8px">
                                                <a href="{donationlink}" class="buttonname">Donate</a>
                                            </p>
                    """.format(description=get_description(ein),donationlink=donationlink)

                    result_txt += """

                                            </div><!-- end charity pictures --> 
                                            <div class="carousel-caption">About
                                            </div>
                                      </div>
                                      <div class="item">
                                            <div id="charitypictures">
                                            

                                            
                                            <p style="text-align:center;padding:8px;"> <b>Highest ranked charities of class '{c_class_str}'</b></p>
                                            
                                            <div class="CSSTableGenerator" style="width:600px;height:400px;">
                                                            <table >
                                """.format(c_class_str=c_class_str)
                    result_txt += get_recommended_charities(c_class)
                    
                    result_txt += """
                    </table>
                      </div>
                                            
                                            </div><!-- end charity pictures -->                                     
                                            <div class="carousel-caption">Comparison
                                            </div>
                                      </div>
                                   </div>
                                   <!-- Carousel nav -->
                                   <a class="carousel-control left" href="#Carousel-{res_num}" 
                                      data-slide="prev"><span class="glyphicon">&lsaquo;</span></a>
                                   <a class="carousel-control right" href="#Carousel-{res_num}" 
                                      data-slide="next"><span class="glyphicon">&rsaquo;</span></a>
                                </div>
                                
                                """.format(res_num=count,charityname=mycharityname)
                # looking for empty result lists. 
                    
                if totalcount == 0:
                    txt = """
                        <p></p>
                        <p>You searched for: <b>'{query}'</b></p>
                        <p>There were no results for your search. </p>
                        <p style="text-align:center"><a href="{search}">Search Again
                                                    </a></p>""".format(query = query,
                                                            search = url_for('search'))
                # For non-empty result lists
                else: 
                    print count
                    print countlimit
                    print totalcount
                    print "found {lenresults} items".format(lenresults=count)
                    if totalcount > countlimit:
                        count_limit_string = "returned more than {lenresults} results. Showing the first {cnt}".format(lenresults=count,cnt=count)
                    else:
                        count_limit_string = "returned {lenresults} results.".format(lenresults=totalcount)

                    txt = """
                        <p></p>
                        <p style="color:#ccc">Your search for: <b>'{query}'</b> {cstr}:</p>
                        <p>{result}</ul></p>
                        <p style="text-align:center"><a href="{search}">Search Again
                                                    </a></p>""".format(query = query,  
                                                            cstr=count_limit_string,
                                                            result = result_txt,
                                                            search = url_for('search'))
                 # if the SQL search fails
            except Exception, e:    
                 txt = """
                        <p></p>
                        <p>Your search was: <b>'{query}'.</b></p> Unfortunately
                        <p> The search failed! The error was:</p>
                        <p>{error}</p>
                        <p>To search again, click 
                        <a href="{search}">here</a>.
                        <p>If you'd like, feel free to email me the error report 
                        at <a href="mailto:qmorgan@gmail.com">qmorgan@gmail.com.</a></p> 
                        """.format(query = query, error=e,
                                                              search = url_for('search'))

        # If the user doesn't submit a query
        else:
            txt = """
                <p><br></p>
                
                <p>No search term was specified. </p>
                <p>Please submit a well-formed query <a href='{}'>here</a></p>""".format(url_for("search"))
        print "attempting to render template"
        return render_template("search.html", txt=unicode(txt.strip(codecs.BOM_UTF8), 'utf-8'))
    else:
        txt = """
        <div class="titlebox">
            <h1 style="color:#E7573C;"> Charity<b>Verity</b> </h1>
            <p style="text-transform:none; font-weight:bold; font-variant:small-caps;">predicting charity ratings to guide effective altruism
            </p>
            <p style="text-transform:none; font-variant:small-caps;">providing ratings for over 175,000 charities
            </p>
        </div>
        <div class="searchbox">
            <form action="search" method="POST">
                <searchfield>
                <p style="
                    margin-bottom: 6px;
                "><input style="text-align: center;" type="text"  name="query" placeholder="Charity Name" id="charityName" class="typeahead" />                 
                <p style="
                    margin-left: 100px;
                    margin-right: 100px;
                "><input style="width:88px;height:30px;text-align: center;"type="submit" class="button"/></p>
                </searchfield>
            </form>
            <p style="text-align:center; text-transform:none; font-variant:small-caps; color:#ccc">v0.3</p>
            
        </div>"""
         
        
        return render_template("search.html", txt = txt)

def check_for_CN_rating(queryein):    
    # SELECT cn.CN_ID, cn.CHARITYNAME, cn.CHARITYCLASS, cn.OVERALL_VALUE, ob.OOB_SCORE 
    #   FROM cn_oob_1 as ob
    #   JOIN charitynavigator as cn
    #   ON cn.CN_ID = ob.CN_ID
    query_template="""
    SELECT cn.CN_ID, cn.OVERALL_VALUE, ob.OOB_SCORE
    FROM (SELECT c.CN_ID, c.OVERALL_VALUE
          FROM charitynavigator as c
          WHERE c.EIN = {}) as cn
    JOIN cn_oob_3 as ob
    WHERE ob.CN_ID = cn.CN_ID
    """.format(str(queryein))

    results = conn.execute(query_template)
    return results


def check_for_donor_advisory(queryein):
    query_template="""
    SELECT c.CN_ID, c.DONORADVISORY
    FROM CNDonorAdvisory as c
    WHERE c.EIN = {}
    """.format(str(queryein))
    results = conn.execute(query_template)
    advisoryid = -1
    for result in results:
        if result['DONORADVISORY'] == 1:
            # we have a donor advisory! 
            advisoryid = result['CN_ID']
    return advisoryid
    

def get_description(queryein):
    query_template = """
    SELECT description FROM missions
    WHERE EIN = {ein}
    """.format(ein=queryein)
    results = conn.execute(query_template)
    description=''
    for result in results:
        description = result['description']
    
    description=description.decode("utf-8")

    if description.isupper():
        desctxt = "<p>{}</p>".format(description.capitalize()) 
    else:
        desctxt = "<p>{}</p>".format(description.encode("utf-8"))

    if description == '':
        desctxt = """<p>A mission statement for this charity is not in our database. Please contact me
         at <a href='mailto:qmorgan@gmail.com'>qmorgan@gmail.com</a> to have a mission statement added.</p>"""    
         # avoid the unicodedecodeerror!

    return desctxt

def get_category(queryein):
    query_template="""
    SELECT e.NTEECAT12 
    FROM nteecat12 as e
    WHERE e.EIN = {}
    """.format(str(queryein))
    results = conn.execute(query_template)
    return results
    
def search_parse(query,countlimit):
    print "searching {}".format(query)
    if "'" in query:
        raise Exception("The characters ', are not allowed ")
        
    #  TODO: Use bindparams to prevent sql injection? 
    
    query_template = """
        SELECT s.NAME, s.CN_SCORE_PREDICT, s.EIN
        FROM cn_predict_3_names as s
        WHERE s.NAME LIKE '%%{}%%'
        ORDER BY s.CN_SCORE_PREDICT DESC
        LIMIT {}
    """.format(query,countlimit+1)
    print query_template
    results = conn.execute(query_template)
    print 'search complete'
    print results
    return results
    #for result in results:
    #    print result
    
    ## Check if unicode in table with regex: LIKE '%[^a-zA-Z0-9]%'

def get_percentile(code,val):
    # SHOULD CACHE ALL OF THESE RESULTS AND LOAD THEM INTO A TABLE
    query_template = """
    SELECT COUNT(CN_SCORE_PREDICT)
    FROM class_score_link_3
    WHERE NTEECAT12 = '{cod}' AND CN_SCORE_PREDICT > {va}
    """.format(cod=code,va=val)
    results = conn.execute(query_template)
    for result in results:
        numfound = result['COUNT(CN_SCORE_PREDICT)']
    
    query_template = """
    SELECT COUNT(CN_SCORE_PREDICT)
    FROM class_score_link_3
    WHERE NTEECAT12 = '{cod}'
    """.format(cod=code)
    results = conn.execute(query_template)
    for result in results:
        numtotal = result['COUNT(CN_SCORE_PREDICT)']
    
    pct = 100.-100.*float(numfound)/float(numtotal)
    return pct

def get_recommended_charities(code):
    query_template = """
    SELECT DISTINCT(c.NAME), c.CN_SCORE_PREDICT
    FROM cn_predict_3_names as c
    JOIN(
        SELECT EIN, CN_SCORE_PREDICT
        FROM class_score_link_3
        WHERE NTEECAT12 = '{cod}'
        ORDER BY CN_SCORE_PREDICT DESC
        LIMIT 15) as ff
    WHERE ff.EIN = c.EIN
    ORDER BY c.CN_SCORE_PREDICT DESC
    """.format(cod=code)
    results = conn.execute(query_template)
    restext = """<tr>
                    <td>Name</td> <td><b>Ranking</b></td>
                  </tr>
                  """
    count = 0
    for result in results:
        restext += """<tr>
                        <td>{name}</td> <td><b>{rating:.2f} / 70</b></td>
                      </tr>
        """.format(name=result['NAME'].title(),rating=result['CN_SCORE_PREDICT'])
        count += 1
        if count > 8:
            break
    return restext
    
    
    
def translate_nteecode(code):
    codedict={
    "AR":"Arts, culture, and humanities",
    "BH":"Higher Education"             ,
    "ED":"Education"                    ,
    "EN":"Environment"                  ,
    "EH":"Hospitals"                    ,
    "HE":"Health"                       ,
    "HU":"Human services"               ,
    "IN":"International"                ,
    "PU":"Public and societal benefit"  ,
    "RE":"Religion"                     ,
    "MU":"Mutual benefit"               ,
    "UN":"Unknown"}
    return codedict[code]

if __name__ == "__main__":
    app.run(port=8000)



