import os, datetime, re, glob,sys
from flask import Flask, request, redirect, url_for, render_template, redirect, url_for, flash
from werkzeug import secure_filename
# from flask_sqlalchemy import SQLAlchemy
from flask.ext.sqlalchemy import SQLAlchemy
import sqlite3
from os.path import exists


basedir = os.path.abspath(os.path.dirname(__file__))

UPLOAD_FOLDER = '.'
ALLOWED_EXTENSIONS = set(['bib'])

application = Flask(__name__) #update 
app = application
app.debug = True

# dbglob = glob.glob('*.db')
# 
# if dbglob: # taking advantage of the 'Falseness' of empty lists
#     db_path = 'sqlite:///' + os.path.join(basedir, dbglob[0])
# else:
#     db_path = 'sqlite:///' + os.path.join(basedir, 'app.db')

import os
import sys
if not os.environ.has_key("MYSQL_PASS"):
    print "You need to set the environment variable  to"
    print "point to your gmail password"
    sys.exit(1)
else: 
    passwd = os.environ.get("MYSQL_PASS")

 
db_path = 'mysql://root:'+passwd+'@localhost/cnavigator'

app.config['SQLALCHEMY_DATABASE_URI'] = db_path
db = SQLAlchemy(app)

app.config.from_object(__name__)

# db.create_all()
db.create_all()


@app.route("/")
def index():
    # right now just force them to go to search
    return "Hello world!"
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
                results = search_parse(query)
                print 'search done'
                result_txt = "<ul>"
                count = 0
                # loop through results and post box
                for result in results:
                    count += 1
                    result_txt += '''
                    <header class="bridgetitle" id="charityname" style="padding-top: 50px;padding-bottom: 10px;">{c_name}</header>
                    '''.format(c_name = str(result['CHARITYNAME']))
                    # if result['OOB_Score'] > 55.0:
                    #     colorstr = "#B1CC9F"
                    # elif result['OOB_Score'] > 40.0:
                    #     colorstr = "#F1DD40"
                    # else:
                    #     colorstr = "#F36E4A"
                    #     
                    # if float(result['OVERALL_VALUE']) > 55.0:
                    #     colorstr2 = "#B1CC9F"
                    # elif float(result['OVERALL_VALUE']) > 40.0:
                    #     colorstr2 = "#F1DD40"
                    # else:
                    #     colorstr2 = "#F36E4A"
                    # don't filter for now.
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
                    result_txt += """ <div class="item active">
                      			        <div id="charitypictures">

                                            <li> 
                                            <p> <b>Class:</b> {c_class} </p>
                                            <h3 style="color:{colorstr}"> Predicted Rating: {c_predict:.2f} / 70</h3>
                                            <p style="color:{colorstr2}"> <i>Actual Rating: {c_value} / 70</i></p>
                                            <br>
                                            
                                            </li>
                                            <img src="http://i.imgur.com/xPg7jZD.png" width="580px" style="position:absolute;z-index:-1"></img>
                      					</div><!-- end charity pictures -->
                                        <div class="carousel-caption">Overview
                                        </div>
                                      </div>
                                     """.format(CN_ID = str(result['CN_ID']),
                                                c_class = str(result['CHARITYCLASS']),
                                                colorstr = colorstr, c_predict=result['OOB_SCORE'],
                                                c_value = str(result['OVERALL_VALUE']),colorstr2 = '#dddddd')#,
                                     #           c_predict = result['OOB_Score'])
                                     # <p> This is higher than <b>XX.X%</b> of all ranked charities of its class</p> 
                                     
                    result_txt += """<div class="item">
                        			        <div id="charitypictures">

                                              <h3 style="color:#8c92ac">Similar charities with higher rankings include:</h3><br><br>
                                              <li>My Incredible Charity: 67.3 / 70</li><br>
                                              <li>A Pretty Great Charity: 64.5 / 70</li><br>
                                              <li>Still Good Charity: 62.2 / 70</li><br>
                                              <li>Yet Another Charity: 62.0 / 70</li><br><br>
                                              <li><i>Each of these will link to my results for the charity</i><br>

                        					</div><!-- end charity pictures --> 
                        					<div class="carousel-caption">Comparison
                        					</div>
                                      </div>
                                      <div class="item">
                        			        <div id="charitypictures">
                                            <p>SAMPLE Summary table (will make it nice with CSS)</p>
                                              <img src="http://i.imgur.com/jghRFbd.png" style="position:absolute;z-index:-1" width="580px"></img>
                                              
                                              

                        					</div><!-- end charity pictures -->                                     
                        					<div class="carousel-caption">Tables
                        					</div>
                                      </div>
                                   </div>
                                   <!-- Carousel nav -->
                                   <a class="carousel-control left" href="#Carousel-{res_num}" 
                                      data-slide="prev"><span class="glyphicon">&lsaquo;</span></a>
                                   <a class="carousel-control right" href="#Carousel-{res_num}" 
                                      data-slide="next"><span class="glyphicon">&rsaquo;</span></a>
                                </div>
                                
                                """.format(res_num=count)
                # looking for empty result lists
                if result_txt == "<ul>":
                    txt = """
                        <p></p>
                        <p>You searched for: <b>'{query}'</b></p>
                        <p>There were no results for your search. </p>
                        <p style="text-align:center"><a href="{search}">Search Again
                                                    </a></p>""".format(query = query,
                                                            search = url_for('search'))
                # for non-empty result lists
                else: 
                    print 'FOUND SOMETHING'
                    txt = """
                        <p></p>
                        <p>Your search for: <b>'{query}'</b> returned {lenresults} results:</p>
                        <p>{result}</ul></p>
                        <p style="text-align:center"><a href="{search}">Search Again
                                                    </a></p>""".format(query = query, lenresults=count,
                                                            result = result_txt,
                                                            search = url_for('search'))
                 # the SQL search fails
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

        return render_template("search.html", txt = txt)
    else:
        txt = """
        <div class="searchbox">
            <form action="search" method="POST">
                <searchfield>
                <p style="padding-left:34%; "><input style="width:50%;text-align: center;" type="text"  name="query" placeholder="Charity Name"/></p>
                <p style="padding-left:44.8%; "><input style="height:30px;text-align: center;"type="submit" class="button"/></p>
                </searchfield>
            </form>
        </div>"""
        return render_template("search.html", txt = txt)

def search_parse(query):
    print "searching {}".format(query)
    # query_template = "SELECT * FROM charitynavigator WHERE CHARITYNAME LIKE '%%{}%%'".format(query)
    if "'" in query:
        raise Exception("The characters ', are not allowed ")
        
    # t = text("""SELECT cn.CN_ID, cn.CHARITYNAME, cn.CHARITYCLASS, cn.OVERALL_VALUE, ob.OOB_SCORE 
    #       FROM cn_oob_1 as ob
    #       JOIN charitynavigator as cn
    #       ON cn.CN_ID = ob.CN_ID
    #       WHERE cn.CHARITYNAME LIKE '\:username'
    #       """).bindparams(query=query)
    query_template = """
    SELECT cn.CN_ID, cn.CHARITYNAME, cn.CHARITYCLASS, cn.OVERALL_VALUE, ob.OOB_SCORE 
    	FROM cn_oob_1 as ob
    	JOIN charitynavigator as cn
    	ON cn.CN_ID = ob.CN_ID
    	WHERE cn.CHARITYNAME LIKE '%%{}%%'
    """.format(query)
    print query_template
    eng = db.create_engine(db_path)
    results = eng.execute(query_template)
    print 'search complete'
    print results
    return results
    #for result in results:
    #    print result


if __name__ == "__main__":
    # app.run(port=5000)
