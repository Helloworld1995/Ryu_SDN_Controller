
import userDao


def test():
    # userDao.Dbutil().insert(1,'10.1.0.2','10.3.0.1','g-g-g-g')
    result=userDao.Dbutil().select('10.1.0.1','10.3.0.1')
    print(result)

test()
print 1*None