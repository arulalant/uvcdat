# Adapted for numpy/ma/cdms2 by convertcdms.py
"""
# Template Boxes and Lines (Pbl) module
"""
#################################################################################
#                                                                               #
# Module:       Template Boxes and Lines (Pbl) module                           #
#                                                                               #
# Copyright:    2000, Regents of the University of California                   #
#               This software may not be distributed to others without          #
#               permission of the author.                                       #
#                                                                               #
# Author:       PCMDI Software Team                                             #
#               Lawrence Livermore NationalLaboratory:                          #
#               support@pcmdi.llnl.gov                                          #
#                                                                               #
# Description:  Python command wrapper for VCS's template boxes and lines       #
#		object.               						#
#                                                                               #
# Version:      4.0                                                             #
#                                                                               #
#################################################################################
#
#
#
#################################################################################
#                                                                               #
# Import: VCS C extension module.                                               #
#                                                                               #
#################################################################################
import _vcs_legacy, queries
from types import *

#################################################################################
#                                                                               #
# Function:	setPblmember                                                    #
#                                                                               #
# Description of Function:                                                      #
# 	Private function to update the VCS canvas plot. If the canvas mode is   #
#       set to 0, then this function does nothing.              		#
#                                                                               #
#                                                                               #
# Example of Use:                                                               #
#      setPblmember(self,name,value)						#
#              where: self is the class (e.g., Pbl)                             #
#                     name is the name of the member that is being changed      #
#                     value is the new value of the member (or attribute)       #
#                                                                               #
#################################################################################
def setPblmember(self,member,attribute,value):
     _vcs_legacy.setPblmember(self.parent, member, attribute, value, self.template_parent.mode)
#     _vcs_legacy.setPblmember(self, member, value, self.parent.mode)

#################################################################################
#                                                                               #
# Function:     getPblmember                                                    #
#                                                                               #
# Description of Function:                                                      #
#       Private function that retrieves the line members from the C             #
#       structure and passes it back to Python.                                 #
#                                                                               #
#                                                                               #
# Example of Use:                                                               #
#      return_value =								#
#      getPblmember(self,name)                                                  #
#              where: self is the class (e.g., Pbl)                             #
#                     name is the name of the member that is being found        #
#                                                                               #
#################################################################################
def getPblmember(self,member,attribute):
     return _vcs_legacy.getPblmember(self,member,attribute)

#############################################################################
#                                                                           #
# Template text (Pbl) Class.                                                #
#                                                                           #
#############################################################################
class Pbl:
    '''
 Class:	Pbl				# Template text

 Description of Pbl Class:
    The Template text object allows the manipulation of line type, width, and color index. 

    This class is used to define an line table entry used in VCS, or it
    can be used to change some or all of the line attributes in an
    existing line table entry.

 Other Useful Functions:
 	     a=vcs_legacy.init()		# Constructor
	     a.show('line')		# Show predefined line objects
             a.update()               	# Updates the VCS Canvas at user's request
             a.mode=1, or 0           	# If 1, then automatic update, else if
                                          0, then use update function to
                                          update the VCS Canvas.

 Example of Use:
    a=vcs_legacy.init()
    To Create a new instance of line use:
     ln=a.createline('new','red') 	# Copies content of 'red' to 'new'
     ln=a.createline('new') 		# Copies content of 'default' to 'new'

    To Modify an existing line use:
     ln=a.getline('red')

    ln.list()  				# Will list all the line attribute values
    ln.color=100			# Range from 1 to 256
    ln.width=100			# Range from 1 to 300

    Specify the line type:
     ln.type='solid'          		# Same as ln.type=0
     ln.type='dash'          		# Same as ln.type=1
     ln.type='dot'          		# Same as ln.type=2
     ln.type='dash-dot'          	# Same as ln.type=3
     ln.type='long-dash'          	# Same as ln.type=4
'''
    #############################################################################
    #                                                                           #
    # Initialize the line attributes.                                           #
    #                                                                           #
    #############################################################################
    def __init__(self, template, template_parent, member=None):
#    def __init__(self, template, member=None):
	#                                                         #
        ###########################################################
	# Initialize the line class and its members               #
        #							  #
	# The getPblmember function retrieves the values of the    #
        # line members in the C structure and passes back the     #
	# appropriate Python Object.                              #
        ###########################################################
	#                                                         #
        self.__dict__['member']=member
        self.__dict__['priority']=getPblmember(template,member,'priority')
        self.__dict__['x1']=getPblmember(template,member,'x1')
        self.__dict__['y1']=getPblmember(template,member,'y1')
        self.__dict__['x2']=getPblmember(template,member,'x2')
        self.__dict__['y2']=getPblmember(template,member,'y2')
        self.__dict__['line']=getPblmember(template,member,'line')
        #                                                         #
        ###########################################################
        # Keep track of the parent and grandparent.               #
        ###########################################################
        #                                                         #
        self.__dict__['parent']=template
        self.__dict__['template_parent']=template_parent

    #############################################################################
    #                                                                           #
    # Set template text  attributes.                                            #
    #                                                                           #
    #############################################################################
    def __setattr__(self, name, value):
        if (self.parent.name == '__removed_from_VCS__'):
           raise ValueError, 'This instance has been removed from VCS.'
        if (name == 'priority'):
           if (isinstance(value, IntType)):
              self.__dict__[name]=value
           else:
              raise ValueError, 'The priority value must be an integer.'
        if (name == 'x1'):
           if (type(value) in (IntType, FloatType)):
              self.__dict__[name]=value
           else:
              raise ValueError, 'The x value must be an integer or float.'
        if (name == 'y1'):
           if (type(value) in (IntType, FloatType)):
              self.__dict__[name]=value
           else:
              raise ValueError, 'The y value must be an integer or float.'
        if (name == 'x2'):
           if (type(value) in (IntType, FloatType)):
              self.__dict__[name]=value
           else:
              raise ValueError, 'The x value must be an integer or float.'
        if (name == 'y2'):
           if (type(value) in (IntType, FloatType)):
              self.__dict__[name]=value
           else:
              raise ValueError, 'The y value must be an integer or float.'
        elif (name == 'line'):
           if (queries.isline(value)==1):
              self.__dict__[name]=value.name
              value = value.name
           elif (type(value) == StringType):
              self.__dict__[name]=value
           else:
              raise ValueError, 'The line value must be a line object.'
        setPblmember(self,self.member,name,value) # update the plot

    #############################################################################
    #                                                                           #
    # List out template text members (attributes).                              #
    #                                                                           #
    #############################################################################
    def list(self):
        if (self.parent.name == '__removed_from_VCS__'):
           raise ValueError, 'This instance has been removed from VCS.'
        print "member = ", self.member
        print "     priority =", self.priority
        print "     x1 =", self.x1
        print "     y1 =", self.y1
        print "     x2 =", self.x2
        print "     y2 =", self.y2
        print "     line =", self.line


#################################################################################
#        END OF FILE								#
#################################################################################
